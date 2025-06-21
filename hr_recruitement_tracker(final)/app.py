
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

from functools import wraps
import os
import sys
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine, engine,text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from database import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from datetime import datetime

now = datetime.now()
formatted_date = now.strftime('%Y-%m-%d')
formatted_time = now.strftime('%H:%M:%S')
formated_datetime = now.strftime('%Y-%m-%d %H:%M:%S')



app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Root route to redirect to login
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # role = request.form.get('role')
        print(username)

        try:
            # Create a connection and execute query
            with engine.connect() as connection:
                result = connection.execute(
                    text('SELECT * FROM users WHERE username = :username'),
                    {'username': username}
                )
                user = result.mappings().fetchone()
                
                if not user:
                    flash('Username not found', 'danger')
                    return render_template('login.html')
                    
                # Access columns by name instead of using dictionary style access
                if user.password != password:
                    flash('Incorrect password', 'danger')
                    return render_template('login.html')
                    
                # if user.role != role:
                #     flash(f'Invalid role selected for user {username}', 'danger')
                #     return render_template('login.html')
                    
                # Set session variables
                session.clear()  # Clear any existing session
                session['username'] = username
                session['user_id'] = user.user_id  # Use column name access
                session['role'] = user.role  # Use column name access
                
                flash(f'Welcome {username}!', 'success')
                
                # Redirect based on role
                if session['role'] == 'recruiter':
                    return redirect(url_for('REC_DASHBOARD',username=user.username))
                elif session['role'] == 'hr':
                    return redirect(url_for('Hr_Dashboard'))  # Fixed HR redirect
                elif session['role'] == 'user':
                    return redirect(url_for('user_dashboard'))
                elif session['role'] =='admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Invalid role', 'danger')
                    return render_template('login.html')
                    
        except Exception as e:
            print(f"Login error: {str(e)}")  # Add debugging
            flash(f'An error occurred: {str(e)}', 'danger')
            return render_template('login.html')
            
    return render_template('login.html')

# Decorator to enforce login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/logout')
def logout():
    session.clear()  # or session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))  # redirect to login or homepage





@app.route('/admin_dashboard' , methods=['GET'])
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    with engine.connect() as conn:
        # Get total employee count
        total_employees = conn.execute(text(
            'SELECT COUNT(emp_id) as employee_count FROM employee'
        )).scalar()
        
        # Get other metrics you need
        # active_jobs = conn.execute(text(
        #     'SELECT COUNT(*) FROM jobs WHERE status = "active"'
        # )).scalar()
        
        # pending_approvals = conn.execute(text(
        #     'SELECT COUNT(*) FROM requests WHERE status = "pending"'
        # )).scalar()

        # conn.commit()
        
    return render_template('admin_dashboard.html',
                        employee_count=total_employees)
                        # jobopening_count=active_jobs,
                        # pending_approvals=pending_approvals)


@app.route('/emp_data', methods=['GET'])
@login_required
def emp_data():
    if session.get('role') != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    try:
        with engine.connect() as conn:
            # Fetch all employee data with all columns
            result = conn.execute(text('''
                SELECT 
                    emp_id, 
                    username, 
                    emp_name, 
                    emp_code, 
                    gender, 
                    phone_num,
                    location, 
                    designation, 
                    department, 
                    dept_id,
                    salary, 
                    joining_date,
                    role,
                    position_id
                FROM employee
                ORDER BY emp_id
            '''))
            
            employees = result.mappings().all()
            
        return render_template('emp_data.html', employees=employees)
        
    except Exception as e:
        flash(f"Error fetching employee data: {str(e)}", 'danger')
        return redirect(url_for('admin_dashboard'))
    


@app.route('/user_dashboard' , methods=['GET','POST'])
@login_required
def user_dashboard():
    # Get the logged-in user's ID from session
    user_id = session['user_id']

    if session.get('role') not in ['user', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('login'))


    
    with engine.connect() as conn:
        # Verify the user exists and get their employee ID
        user = conn.execute(text('''
            SELECT U.user_id, U.username, E.emp_id, E.emp_name ,E.department , E.dept_id
            FROM users U
            JOIN employee E ON U.username = E.username
            WHERE U.user_id = :user_id
        '''), {'user_id': user_id}).fetchone()
        
        
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('login'))
        

        
        # Get employee details (with additional verification)
        emp_details = conn.execute(text('''
            SELECT e.emp_id, e.emp_name, e.dept_id, e.position_id,
                   d.dept_name, p.position_name
            FROM employee e
            JOIN m_dept d ON e.dept_id = d.dept_id
            JOIN m_position p ON e.position_id = p.position_id
            WHERE e.emp_id = :emp_id
        '''), {'emp_id': user.user_id}).fetchone()
        
        if not emp_details:
            flash('Employee details not found', 'danger')
            return redirect(url_for('login'))
        
        # Set session variables
        session['emp_id'] = emp_details.emp_id
        session['emp_name'] = emp_details.emp_name
        session['dept_id'] = emp_details.dept_id
        session['position_id'] = emp_details.position_id

        # Get all employees for dropdown
        # employees = conn.execute(text('''
        #     SELECT emp_id,emp_name FROM employee e
        #     JOIN users u ON e.emp_id = u.user_id
            
        # ''')).fetchall()

        employees = [{
            'emp_id': user.emp_id,
            'emp_name': user.emp_name,
            'dept_id': user.dept_id,
            'department': user.department
        }]
        
        # Get all departments for dropdown
        departments = conn.execute(text('''
            SELECT dept_id, dept_name FROM m_dept d
                                        
        ''')).fetchall()
        
        # Get all positions for dropdown
        positions = conn.execute(text('''
            SELECT position_id, position_name FROM m_position
        ''')).fetchall()

        status=conn.execute(text('''
            SELECT status_id, status_name FROM m_status
        ''')).fetchall()
        
        # Get job statistics - STRICTLY for this user only
        stats = conn.execute(text('''
            SELECT 
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_jobs,
                SUM(CASE WHEN status = 'Assigned' THEN 1 ELSE 0 END) as assigned_jobs,
                SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_jobs
            FROM jobopening
            WHERE emp_id = :emp_id
        '''), {'emp_id': session['emp_id']}).fetchone()
        
        # Get recent jobs - STRICTLY for this user only
        recent_jobs = conn.execute(text('''
            SELECT j.job_id, j.position_name, d.dept_name, j.emp_name, j.status, j.created_at
            FROM jobopening j
            JOIN m_dept d ON j.dept_id = d.dept_id
            WHERE j.emp_id = :emp_id
            ORDER BY j.created_at DESC
            
        '''), {'emp_id': user.user_id}).fetchall()
        
        # Get all jobs - STRICTLY for this user only
        all_jobs = conn.execute(text('''
            SELECT j.*, d.dept_name, p.position_name, s.status_name
            FROM jobopening j
            JOIN m_dept d ON j.dept_id = d.dept_id
            JOIN m_position p ON j.position_id = p.position_id
            JOIN m_status s ON j.status = s.status_id
            WHERE j.emp_id = :emp_id
            ORDER BY j.created_at DESC
        '''), {'emp_id': session['emp_id']}).mappings().fetchall()


        
        all_job = conn.execute(text('''
        SELECT j.job_id, j.emp_id, j.emp_name, j.dept_id, d.dept_name, 
            j.position_id, p.position_name, j.status, j.created_at
        FROM jobopening j
        JOIN m_dept d ON j.dept_id = d.dept_id
        JOIN m_position p ON j.position_id = p.position_id
        WHERE j.emp_id = :emp_id
    '''), {'emp_id': session['emp_id']}).mappings().fetchall()
        

       
         # Debugging line to check fetched jobs
        


        
    return render_template('user_dashboard.html', 
                        all_job=all_job,
                         user=user,
                         emp_details=emp_details,
                         employees=employees,
                         departments=departments,
                         positions=positions,
                         total_jobs=stats.total_jobs,
                         open_jobs=stats.open_jobs,
                         assigned_jobs=stats.assigned_jobs,
                         closed_jobs=stats.closed_jobs,
                         recent_jobs=recent_jobs,
                         all_jobs=all_jobs,
                         status=status)

@app.route('/submit_job_opening', methods=['POST'])
@login_required
def submit_job_opening():
    user_id = session['user_id']
    if request.method == 'POST':
        try:
            # Get all form data
            emp_id = request.form.get('emp_id')
            dept_id = request.form.get('dept_id')
            position_id = request.form.get('position_id')
            emp_name = request.form.get('emp_name')
            dept_name = request.form.get('dept_name')
            position_name = request.form.get('position_name')
            status = request.form.get('status', 'Open')
            assigned_status = request.form.get('assigned_status', 'Not Assigned')
            description = request.form.get('description', '')
            created_at = request.form.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            with engine.connect() as conn:
                # Insert the new job opening
                conn.execute(text('''
                    INSERT INTO jobopening (
                        emp_id, dept_id,emp_name, position_name,position_id,
                        created_at,status, assigned_status, dept_name,position_closure
                        
                        
                    ) VALUES (
                        :emp_id, :dept_id,:emp_name, :position_name,:position_id,
                        :created_at,:status, :assigned_status, :dept_name,:position_closure
                    )
                '''), {
                    'emp_id' :emp_id, 
                    'dept_id': dept_id,
                    'emp_name':emp_name, 
                    'position_name':position_name,
                    'position_id':position_id,
                    'created_at':created_at,
                    'status':status,
                    'assigned_status':assigned_status,
                    'dept_name':dept_name,
                    'position_closure':'Open'
                })
                conn.commit()
                
                flash('Job submitted successfully!', 'success')

                
                
                return redirect(url_for('user_dashboard'))
                
        except Exception as e:
            flash(f'Error submitting job: {str(e)}', 'danger')
            return redirect(url_for('user_dashboard'))
        
@app.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    
    role = session.get('role', '').lower()

    try:
        with engine.connect() as conn:
            # HR can delete any job; users can only delete their own
            if role == 'user':
                job_check = conn.execute(text('''
                    SELECT job_id FROM jobopening 
                    WHERE job_id = :job_id 
                '''), {
                    'job_id': job_id,
                    
                }).fetchone()

                if not job_check:
                    flash('You are not authorized to delete this job.', 'danger')
                    return redirect(url_for('user_dashboard'))

            # Delete the job (for both HR and allowed users)
            with engine.connect() as conn:
                conn.execute(text('DELETE FROM jobopening WHERE job_id = :job_id'), {'job_id': job_id})
                conn.commit()

                flash('Job deleted successfully.', 'success')
                return redirect(url_for('user_dashboard'))

    except Exception as e:
        flash(f'Error deleting job: {str(e)}', 'danger')
        return redirect(url_for('user_dashboard'))

@app.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
     # Debugging line to check user_id
    

    if session ['role'] != 'user':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    try:
        with engine.begin() as conn:  # use engine.begin() to ensure commit
            job = conn.execute(text('''
                SELECT * FROM jobopening 
                WHERE job_id = :job_id 
            '''), {'job_id': job_id}).fetchone()

            if not job:
                flash('Job not found or not authorized.', 'danger')
                return redirect(url_for('user_dashboard'))

            if request.method == 'POST':
                updated_data = {
                    'position_name': request.form.get('position_name'),
                    'position_id': request.form.get('position_id'),
                    'status': request.form.get('status'),
                    'assigned_status': request.form.get('assigned_status'),
                    
                    'job_id': job_id
                }
                print(updated_data)  # Debugging line to check updated data

                conn.execute(text('''
                    UPDATE jobopening
                        SET position_name = :position_name, 
                        position_id = :position_id, 
                        status = :status, 
                        assigned_status = :assigned_status
                    WHERE job_id = :job_id
                '''), updated_data)


                flash('Job updated successfully.', 'success')
                return redirect(url_for('user_dashboard'))

            # Fetch dropdown options
            positions = conn.execute(text('SELECT position_id, position_name FROM m_position')).fetchall()
            status = conn.execute(text('SELECT status_id, status_name FROM m_status')).fetchall()

            return render_template('edit_job.html', job=job, positions=positions, status=status)

    except Exception as e:
        flash(f'Error editing job: {str(e)}', 'danger')
        return redirect(url_for('user_dashboard'))
    
def get_emp_id_from_username():
    username = session.get('username')
    print(username)
    if not username:
        return None

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT emp_id FROM employee WHERE username = :username"),
            {'username': username}
        ).mappings().fetchone()

        return result['emp_id'] if result else None

    




@app.route('/Hr_Dashboard')
@login_required
def Hr_Dashboard():

    if session.get('role') not in ['hr', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
    
    # Get emp_id using the helper
    hr_emp_id = get_emp_id_from_username()
    session['hr_emp_id'] = hr_emp_id
    

    
    if not hr_emp_id:
        flash("Unable to identify HR user. Please log in again.", "danger")
        return redirect(url_for('login'))

    with engine.connect() as connection:
        recruiters = connection.execute(text("""
            SELECT 
                e.emp_name, 
                e.emp_id,
                e.username,
                e.emp_code,
                e.designation, 
                e.department, 
                e.phone_num, 
                r.recruiter_emp_id
            FROM HR_RECRUITER r
            JOIN employee e ON r.recruiter_emp_id = e.emp_id
            WHERE r.hr_emp_id = :hr_id
        """), {'hr_id': hr_emp_id}).mappings().fetchall()
        

        result = connection.execute(text("""
            SELECT COUNT(*) AS total FROM HR_RECRUITER
            WHERE hr_emp_id = :hr_id
        """), {'hr_id': hr_emp_id}).mappings().first()

        total_recruiters=result['total'] if result else 0

        jobs=connection.execute(text(
            """select * from jobopening""")
            ).mappings().fetchall()
        

        employe = connection.execute(
        text("""SELECT emp_id, emp_name FROM employee""")
        ).mappings().fetchall()

        assigned_data=connection.execute(text(
            '''
                select j.job_assigned_id,j.job_id,j.emp_name,j.hr_emp_id,j.recruiter_emp_id,
                j.dept_name,j.dept_id,j.position_name,
                j.position_id,j.assigned_status,j.assigned_date
                from job_assigned j
                where j.hr_emp_id = :hr_emp_id
            '''), {'hr_emp_id': hr_emp_id}).mappings().fetchall()
        
        
        employee_data = connection.execute(text("""
        SELECT * 
        FROM employee e
        JOIN HR_Recruiter r ON e.emp_id = r.hr_emp_id
        WHERE e.emp_id = :hr_emp_id
    """), {'hr_emp_id': hr_emp_id}).mappings().fetchone()




         # Debugging line to check fetched jobs
        

        return render_template('Hr_Dashboard.html', recruiters=recruiters, total_recruiters=total_recruiters,
                              jobs=jobs,employe=employe, username=session.get('username'),assigned_data=assigned_data,
                              employee_data=employee_data)
    
@app.route('/job_openings')
@login_required
def job_openings():
    hr_emp_id = get_emp_id_from_username()

    if not hr_emp_id:
        flash("Unable to identify HR user. Please log in again.", "danger")
        return redirect(url_for('login'))

    with engine.connect() as connection:
        # Get all job openings
        jobs = connection.execute(text("SELECT * FROM jobopening")).mappings().fetchall()

        # Get recruiters associated with this HR
        recruiters = connection.execute(text("""
            SELECT e.emp_id, e.emp_name
            FROM HR_RECRUITER hr
            JOIN employee e ON e.emp_id = hr.recruiter_emp_id
            WHERE hr.hr_emp_id = :hr_emp_id
        """), {'hr_emp_id': hr_emp_id}).mappings().fetchall()

    return render_template('job_openings.html', jobs=jobs, recruiters=recruiters)


    


@app.route('/assign_job', methods=['POST'])
def assign_job():
    if request.method == 'POST':  # ✅ Fix the comparison
        try:
            # print("Form data received:", request.form)
            job_id = request.form.get('job_id')
            emp_name = request.form.get('emp_name')
            hr_emp_id = request.form.get('hr_emp_id')
            recruiter_emp_id = request.form.get('recruiter_emp_id')
            dept_name = request.form.get('dept_name')
            dept_id = request.form.get('dept_id')
            position_name = request.form.get('position_name')
            position_id = request.form.get('position_id')
            assigned_status = request.form.get('assigned_status')
            assigned_date = datetime.now()
            


            with engine.connect() as connection:
                connection.execute(text("""
                    INSERT INTO job_assigned 
                    (job_id, emp_name, hr_emp_id, recruiter_emp_id, dept_name, dept_id, position_id, position_name, assigned_status, assigned_date)
                    VALUES 
                    (:job_id, :emp_name, :hr_emp_id, :recruiter_emp_id, :dept_name, :dept_id, :position_id, :position_name, :assigned_status, :assigned_date)
                """), {
                    'job_id': job_id,
                    'emp_name': emp_name,
                    'hr_emp_id': hr_emp_id,
                    'recruiter_emp_id': recruiter_emp_id,
                    'dept_name': dept_name,
                    'dept_id': dept_id,
                    'position_name': position_name,
                    'position_id': position_id,
                    
                    'assigned_status': assigned_status,
                    'assigned_date': assigned_date
                })
                
                connection.commit()

                if assigned_status == 'Assigned':
                    connection.execute(text("""
                        UPDATE jobopening
                        SET status = (
                            SELECT status_name FROM m_status WHERE status_name = 'Assigned' LIMIT 1
                        )
                        WHERE job_id = :job_id
                    """), {'job_id': job_id})
                else:
                    ("error")

                connection.commit()

                
                

            flash("Job assigned successfully!", "success")
            return redirect(url_for('job_openings'))
              # ✅ This should match your route function

        except Exception as e:
            print("Error assigning job:", e)
            flash("Error assigning job. Please check the input data.", "danger")
            return redirect(url_for('job_openings'))  # ✅ This should match your route function
        
@app.route('/job_assigned_table', methods=['GET'])
@login_required
def job_assigned_table():
    # Get emp_id of HR from session or helper
    hr_emp_id = get_emp_id_from_username()
    session['hr_emp_id'] = hr_emp_id

    if not hr_emp_id:
        flash("Unable to identify HR user. Please log in again.", "danger")
        return redirect(url_for('login'))

    recruiter_filter = request.args.get('recruiter_id')  # Recruiter selected in dropdown

    with engine.connect() as connection:
        # Fetch recruiters for filter dropdown
        recruiters = connection.execute(text("""
            SELECT e.emp_id, e.emp_name
            FROM HR_RECRUITER r
            JOIN employee e ON r.recruiter_emp_id = e.emp_id
            WHERE r.hr_emp_id = :hr_id
        """), {'hr_id': hr_emp_id}).mappings().fetchall()

        # Apply filtering logic
        if recruiter_filter:
            assigned_data = connection.execute(text("""
                SELECT * FROM job_assigned
                WHERE hr_emp_id = :hr_id AND recruiter_emp_id = :recruiter_id
            """), {
                'hr_id': hr_emp_id,
                'recruiter_id': int(recruiter_filter)
            }).mappings().fetchall()
        else:
            assigned_data = connection.execute(text("""
                SELECT * FROM job_assigned
                WHERE hr_emp_id = :hr_id
            """), {'hr_id': hr_emp_id}).mappings().fetchall()

    return render_template('job_assigned_table.html',
                           recruiters=recruiters,
                           assigned_data=assigned_data,
                           selected_recruiter=recruiter_filter)





# @app.route('/REC_DASHBOARD')
@app.route('/REC_DASHBOARD/<string:username>', methods=['GET'])
def REC_DASHBOARD(username):
    if 'username' not in session or session.get('role') not in ['recruiter', 'hr', 'admin']:
        flash('Access denied. Please log in.', 'danger')
        return redirect(url_for('login'))
    print(username)

    with engine.connect() as conn:
        # ✅ Recruiter details
        recruiter_data = conn.execute(text('''
            SELECT * FROM employee e
            join users u
            on u.username= e.username                            
            WHERE u.username = :username AND u.role = 'recruiter'
        '''), {'username': username}).fetchone()

        if not recruiter_data:
            flash('Recruiter not found.', 'danger')
            return redirect(url_for('login'))
        
        emp_id = recruiter_data.emp_id 

        # ✅ HR details from hr_recruiter table
        hr_data = conn.execute(text('''
            SELECT e.emp_name AS hr_name, e.phone_num AS hr_phone
            FROM hr_recruiter hr
            JOIN employee e ON hr.hr_emp_id = e.emp_id
            WHERE hr.recruiter_emp_id = :emp_id
        '''), {'emp_id': emp_id}).fetchone()

         # ✅ Fetch candidates only for this recruiter
        candidates = conn.execute(text('''
            SELECT * FROM candidates
            WHERE recruiter_emp_id = :emp_id
        '''), {'emp_id': emp_id}).mappings().fetchall()
      

        # ✅ Job assignments for this recruiter
        jobs = conn.execute(text('''
            SELECT  ja.emp_name,ja.recruiter_emp_id,ja.hr_emp_id,
                    ja.dept_name,  ja.position_name,
                   ja.assigned_status, ja.assigned_date, ja.job_assigned_id, ja.job_id
            FROM job_assigned ja            
            WHERE ja.recruiter_emp_id = :emp_id
        '''), {'emp_id': emp_id}).fetchall()

    return render_template('REC_DASHBOARD.html',
                           recruiter=recruiter_data,
                           hr=hr_data,
                           jobs=jobs,
                           candidates=candidates)

@app.route('/add_candidate/<int:job_id>', methods=['GET', 'POST'])
def add_candidate(job_id):
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    UPLOAD_FOLDER = os.path.join('static', 'candidates', 'cvs')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    with engine.connect() as conn:
        job = conn.execute(text("SELECT * FROM job_assigned WHERE job_id = :job_id"),
                           {"job_id": job_id}).mappings().fetchall()
        
        print(job)

        if request.method == 'POST':
            try:
                file = request.files.get('cv_upload')
                if file and allowed_file(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"{request.form['candidate_name']}_{job_id}_cv.{ext}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                else:
                    flash('Invalid file format', 'danger')
                    return redirect(url_for('add_candidate', job_id=job_id))

                data = {
                    'candidate_name': request.form.get('candidate_name'),
                    'hr_emp_id': request.form.get('hr_emp_id'),
                    'recruiter_emp_id': request.form.get('recruiter_emp_id'),
                    'dept_name': request.form.get('dept_name'),
                    'candidate_email': request.form.get('candidate_email'),
                    'candidate_phone': request.form.get('candidate_phone'),
                    'candidate_address': request.form.get('candidate_address'),
                    'candidate_education': request.form.get('candidate_education'),
                    'candidate_skills': request.form.get('candidate_skills'),
                    'candidate_experience': request.form.get('candidate_experience'),
                    'current_company': request.form.get('current_company'),
                    'current_designation': request.form.get('current_designation'),
                    'current_salary': request.form.get('current_salary'),
                    'expected_salary': request.form.get('expected_salary'),
                    'current_location': request.form.get('current_location'),
                    'current_industry': request.form.get('current_industry'),
                    'position_name': request.form.get('position_name'),
                    'assigned_date': request.form.get('assigned_date'),
                    'status': request.form.get('status'),
                    'job_id': job_id,
                    'source': request.form.get('source'),
                    'cv_upload': filename,
                    'job_assigned_id':request.form.get('job_assigned_id')
                }

                print("Data inserting:", data)

                query = text("""INSERT INTO candidates (
                    candidate_name, hr_emp_id, recruiter_emp_id, dept_name, candidate_email,
                    candidate_phone, candidate_address, candidate_education, candidate_skills,
                    candidate_experience, current_company, current_designation, current_salary,
                    expected_salary, current_location, current_industry, position_name,
                    assigned_date, status, job_id, source, cv_upload,job_assigned_id
                ) VALUES (
                    :candidate_name, :hr_emp_id, :recruiter_emp_id, :dept_name, :candidate_email,
                    :candidate_phone, :candidate_address, :candidate_education, :candidate_skills,
                    :candidate_experience, :current_company, :current_designation, :current_salary,
                    :expected_salary, :current_location, :current_industry, :position_name,
                    :assigned_date, :status, :job_id, :source, :cv_upload,:job_assigned_id
                )""")

                conn.execute(query, data)
                conn.commit()

                flash("Candidate added successfully!", "success")
                return redirect(url_for('REC_DASHBOARD', username=session.get('username')))


            except Exception as e:
                print("Exception:", e)
                flash("Error while adding candidate.", "danger")

                
        return render_template('add_candidates.html', job=job)

@app.route('/candidates', methods=['GET','POST'])
def candidates():
    if session.get('role') != 'recruiter':
        return redirect(url_for('login'))

    recruiter_username = session.get('username')

    with engine.connect() as connection:
        # Fetch recruiter info
        recruiter_result = connection.execute(
            text("SELECT * FROM employee WHERE username = :username"),
            {'username': recruiter_username}
        ).fetchone()

        if recruiter_result is None:
            flash("Recruiter not found.")
            return redirect(url_for('login'))

        recruiter_emp_id = recruiter_result.emp_id

        # Fetch candidates linked to this recruiter
        candidates_result = connection.execute(
            text("SELECT * FROM candidates WHERE recruiter_emp_id = :recruiter_emp_id"),
            {'recruiter_emp_id': recruiter_emp_id}
        ).fetchall()

    return render_template('candidates.html', candidates=candidates_result)

@app.route('/add_candidate_activity/<int:candidate_id>', methods=['GET', 'POST'])
def add_candidate_activity(candidate_id):
    if session.get('role') != 'recruiter':
        return redirect(url_for('login'))

    recruiter_username = session.get('username')
    print("Recruiter Username:", recruiter_username)

    # Step 1: Get recruiter and candidate info
    with engine.connect() as connection:
        recruiter_result = connection.execute(
            text("SELECT * FROM employee WHERE username = :username"),
            {'username': recruiter_username}
        ).fetchone()

        if recruiter_result is None:
            flash("Recruiter not found.")
            return redirect(url_for('login'))

        recruiter_emp_id = recruiter_result.emp_id

        candidate = connection.execute(
            text("""
                SELECT * FROM candidates 
                WHERE recruiter_emp_id = :recruiter_emp_id AND candidate_id = :candidate_id
            """),
            {'recruiter_emp_id': recruiter_emp_id, 'candidate_id': candidate_id}
        ).fetchone()

        if candidate is None:
            flash("Candidate not found.", "danger")
            return redirect(url_for('candidates'))

        candidate_data = dict(candidate._mapping)

    # Step 2: Handle form submission
    if request.method == 'POST':
        remarks = request.form.get('Remarks')
        activity_date = request.form.get('activity_date')
        activity_description = request.form.get('activity_description')

        with engine.begin() as connection:
            connection.execute(text('''
                INSERT INTO candidates_activity (
                    candidate_id, candidate_name, hr_emp_id, recruiter_emp_id, dept_name, candidate_email,
                    candidate_phone, candidate_address, candidate_education, candidate_skills,
                    candidate_experience, current_company, current_designation, current_salary,
                    expected_salary, current_location, current_industry, position_name, assigned_date,
                    status, job_id, remarks, activity_date, activity_description
                )
                VALUES (
                    :candidate_id, :candidate_name, :hr_emp_id, :recruiter_emp_id, :dept_name, :candidate_email,
                    :candidate_phone, :candidate_address, :candidate_education, :candidate_skills,
                    :candidate_experience, :current_company, :current_designation, :current_salary,
                    :expected_salary, :current_location, :current_industry, :position_name, :assigned_date,
                    :status, :job_id, :remarks, :activity_date, :activity_description
                )
            '''), {
                'candidate_id': request.form.get('candidate_id'),
                'candidate_name': request.form.get('candidate_name'),
                'hr_emp_id': request.form.get('hr_emp_id'),
                'recruiter_emp_id': request.form.get('recruiter_emp_id'),
                'dept_name': request.form.get('dept_name'),
                'candidate_email': request.form.get('candidate_email'),
                'candidate_phone': request.form.get('candidate_phone'),
                'candidate_address': request.form.get('candidate_address'),
                'candidate_education': request.form.get('candidate_education'),
                'candidate_skills': request.form.get('candidate_skills'),
                'candidate_experience': request.form.get('candidate_experience'),
                'current_company': request.form.get('current_company'),
                'current_designation': request.form.get('current_designation'),
                'current_salary': request.form.get('current_salary'),
                'expected_salary': request.form.get('expected_salary'),
                'current_location': request.form.get('current_location'),
                'current_industry': request.form.get('current_industry'),
                'position_name': request.form.get('position_name'),
                'assigned_date': request.form.get('assigned_date'),
                'status': request.form.get('status'),
                'job_id': request.form.get('job_id'),
                'remarks': remarks,
                'activity_date': activity_date,
                'activity_description': activity_description
            })

            

        flash("Candidate activity added successfully!", "success")
        return redirect(url_for('view_candidate_activity', candidate_id=candidate_id))

    # ✅ Always return the form template
    return render_template('add_candidate_activity.html', candidate=candidate_data)



@app.route('/view_candidate_activity/<int:candidate_id>')
def view_candidate_activity(candidate_id):
    if session.get('role') != 'recruiter':
        return redirect(url_for('login'))

    recruiter_username = session.get('username')

    with engine.connect() as conn:
        # Get recruiter emp_id
        recruiter = conn.execute(
            text("SELECT emp_id FROM employee WHERE username = :username"),
            {'username': recruiter_username}
        ).fetchone()

        if recruiter is None:
            flash("Recruiter not found.")
            return redirect(url_for('login'))

        emp_id = recruiter.emp_id

        # Fetch all activity records for this candidate by this recruiter
        activities = conn.execute(text('''
            SELECT * FROM candidates_activity
            WHERE recruiter_emp_id = :emp_id AND candidate_id = :candidate_id
            ORDER BY activity_date ASC
        '''), {
            'emp_id': emp_id,
            'candidate_id': candidate_id
        }).mappings().fetchall()

        
    return render_template('view_candidate_activity.html', activities=activities)


@app.route('/position_closure_form/<int:candidate_id>', methods=['GET', 'POST'])
def position_closure(candidate_id): 
    if session.get('role') != 'recruiter':
        return redirect(url_for('login'))

    recruiter_username = session.get('username')
    print("Recruiter Username:", recruiter_username)

    with engine.connect() as connection:
        recruiter_result = connection.execute(
            text("SELECT * FROM employee WHERE username = :username"),
            {'username': recruiter_username}
        ).fetchone()

        if recruiter_result is None:
            flash("Recruiter not found.")
            return redirect(url_for('login'))

        recruiter_emp_id = recruiter_result.emp_id
        print(recruiter_emp_id)

        # ✅ Get most recent "Joined" activity for the candidate
        activity = connection.execute(text('''
            SELECT * FROM candidates_activity
            WHERE candidate_id = :candidate_id AND recruiter_emp_id = :recruiter_emp_id AND remarks = 'Joined'
            ORDER BY activity_date DESC LIMIT 1
        '''), {
            'candidate_id': candidate_id,
            'recruiter_emp_id': recruiter_emp_id
        }).mappings().fetchone()

        if not activity:
            flash("No 'Joined' activity found for this candidate.", "warning")
            return redirect(url_for('view_candidate_activity', candidate_id=candidate_id))

    if request.method == 'POST':
        # Collect manually filled values
        joining_date = request.form.get('joining_date')
        salary = request.form.get('salary')

        # Insert data into position_closure
        with engine.begin() as connection:
    # Insert into position_closure
            connection.execute(text('''
                INSERT INTO position_closure (
                    candidate_name, hr_emp_id, recruiter_emp_id, dept_name,
                    candidate_email, candidate_phone, candidate_address,
                    candidate_education, candidate_skills, candidate_experience,
                    current_designation, current_location, position_name, job_id,
                    status, joining_date, salary, candidate_id
                )
                VALUES (
                    :candidate_name, :hr_emp_id, :recruiter_emp_id, :dept_name,
                    :candidate_email, :candidate_phone, :candidate_address,
                    :candidate_education, :candidate_skills, :candidate_experience,
                    :current_designation, :current_location, :position_name, :job_id,
                    :status, :joining_date, :salary, :candidate_id
                )
            '''), {
                'candidate_name': activity['candidate_name'],
                'hr_emp_id': activity['hr_emp_id'],
                'recruiter_emp_id': activity['recruiter_emp_id'],
                'dept_name': activity['dept_name'],
                'candidate_email': activity['candidate_email'],
                'candidate_phone': activity['candidate_phone'],
                'candidate_address': activity['candidate_address'],
                'candidate_education': activity['candidate_education'],
                'candidate_skills': activity['candidate_skills'],
                'candidate_experience': activity['candidate_experience'],
                'current_designation': activity['current_designation'],
                'current_location': activity['current_location'],
                'position_name': activity['position_name'],
                'job_id': activity['job_id'],
                'status': activity['remarks'],
                'joining_date': joining_date,
                'salary': salary,
                'candidate_id': activity['candidate_id']
            })

            # ✅ Move this inside the same connection block
            if activity['remarks'].lower() == 'joined':
                connection.execute(text("""
                    UPDATE jobopening
                    SET position_closure = 'Closed'
                    WHERE job_id = :job_id
                """), {'job_id': activity['job_id']})
            with engine.begin() as connection:
                # Insert into position_closure
                connection.execute(text('''
                    INSERT INTO position_closure (
                        candidate_name, hr_emp_id, recruiter_emp_id, dept_name,
                        candidate_email, candidate_phone, candidate_address,
                        candidate_education, candidate_skills, candidate_experience,
                        current_designation, current_location, position_name, job_id,
                        status, joining_date, salary, candidate_id
                    )
                    VALUES (
                        :candidate_name, :hr_emp_id, :recruiter_emp_id, :dept_name,
                        :candidate_email, :candidate_phone, :candidate_address,
                        :candidate_education, :candidate_skills, :candidate_experience,
                        :current_designation, :current_location, :position_name, :job_id,
                        :status, :joining_date, :salary, :candidate_id
                    )
                '''), {
                    'candidate_name': activity['candidate_name'],
                    'hr_emp_id': activity['hr_emp_id'],
                    'recruiter_emp_id': activity['recruiter_emp_id'],
                    'dept_name': activity['dept_name'],
                    'candidate_email': activity['candidate_email'],
                    'candidate_phone': activity['candidate_phone'],
                    'candidate_address': activity['candidate_address'],
                    'candidate_education': activity['candidate_education'],
                    'candidate_skills': activity['candidate_skills'],
                    'candidate_experience': activity['candidate_experience'],
                    'current_designation': activity['current_designation'],
                    'current_location': activity['current_location'],
                    'position_name': activity['position_name'],
                    'job_id': activity['job_id'],
                    'status': activity['remarks'],
                    'joining_date': joining_date,
                    'salary': salary,
                    'candidate_id': activity['candidate_id']
                })
                connection.commit()

                # ✅ Move this inside the same connection block
                if activity['remarks'].lower() == 'joined':
                    connection.execute(text("""
                        UPDATE jobopening
                        SET position_closure = 'Closed'
                        WHERE job_id = :job_id
                    """), {'job_id': activity['job_id']})

                connection.commit()


                flash("Position closure details submitted successfully.", "success")
                return redirect(url_for('candidate_joined', candidate_id=candidate_id))

    # Render the form with fetched activity
    return render_template("position_closure_form.html", activity=activity)


# @app.route('/candidate_joined')
# def candidate_joined():
#     if session.get('role') != 'recruiter':
#         return redirect(url_for('login'))

#     recruiter_username = session.get('username')

#     with engine.connect() as conn:
#         # Get recruiter emp_id from their username
#         recruiter_query = conn.execute(text("""
#             SELECT emp_id FROM employee WHERE username = :username
#         """), {'username': recruiter_username}).mappings().first()

#         if not recruiter_query:
#             flash("Recruiter not found.", "danger")
#             return redirect(url_for('login'))

#         recruiter_id = recruiter_query['emp_id']

#         # Fetch joined candidates from candidate + position_closure tables only
#         result = conn.execute(text("""
#             SELECT 
#                 pc.*, 
#                 c.candidate_name, c.candidate_email, c.candidate_phone, c.candidate_address,
#                 c.candidate_education, c.candidate_skills, c.candidate_experience,
#                 c.current_designation, c.current_location
#             FROM position_closure pc
#             JOIN candidates c ON pc.candidate_id = c.candidate_id
#             WHERE pc.status = 'joined' AND pc.recruiter_emp_id = :recruiter_id
#         """), {'recruiter_id': recruiter_id}).mappings().fetchall()

#     return render_template("candidate_joined.html", result=result)

@app.route('/candidate_joined')
def candidate_joined():
    if 'username' not in session or 'role' not in session:
        flash("Please log in to view candidates.", "warning")
        return redirect(url_for('login'))

    username = session['username']
    role = session['role']

    with engine.connect() as conn:
        user_data = conn.execute(text("""
            SELECT emp_id FROM employee WHERE username = :username
        """), {'username': username}).mappings().first()

        if not user_data:
            flash("User not found in employee table.", "danger")
            return redirect(url_for('login'))

        emp_id = user_data['emp_id']

        # Admin sees everything
        if role == 'admin':
            result = conn.execute(text("""
                SELECT pc.*, c.*
                FROM position_closure pc
                JOIN candidates c ON pc.candidate_id = c.candidate_id
                WHERE pc.status = 'joined'
            """)).mappings().fetchall()

        # HR sees joined candidates under their mapped recruiters
        elif role == 'hr':
            recruiter_ids = conn.execute(text("""
                SELECT recruiter_emp_id FROM HR_RECRUITER WHERE hr_emp_id = :hr_id
            """), {'hr_id': emp_id}).mappings().fetchall()

            recruiter_emp_ids = [r['recruiter_emp_id'] for r in recruiter_ids]

            if recruiter_emp_ids:
                result = conn.execute(text("""
                    SELECT pc.*, c.*
                    FROM position_closure pc
                    JOIN candidates c ON pc.candidate_id = c.candidate_id
                    WHERE pc.status = 'joined' AND pc.recruiter_emp_id IN :ids
                """), {'ids': tuple(recruiter_emp_ids)}).mappings().fetchall()
            else:
                result = []

        # Recruiter sees their own joined candidates
        elif role == 'recruiter':
            result = conn.execute(text("""
                SELECT pc.*, c.*
                FROM position_closure pc
                JOIN candidates c ON pc.candidate_id = c.candidate_id
                WHERE pc.status = 'joined' AND pc.recruiter_emp_id = :emp_id
            """), {'emp_id': emp_id}).mappings().fetchall()

        # User sees joined candidates for jobs they created
        elif role == 'user':
            job_ids = conn.execute(text("""
                SELECT job_id FROM jobopening WHERE emp_id = :emp_id
            """), {'emp_id': emp_id}).mappings().fetchall()

            job_id_list = [j['job_id'] for j in job_ids]

            if job_id_list:
    # Dynamically construct IN clause with bound parameters
                placeholders = ", ".join([f":id{i}" for i in range(len(job_id_list))])
                params = {f"id{i}": job_id_list[i] for i in range(len(job_id_list))}

                result = conn.execute(text(f"""
                    SELECT pc.*, c.*
                    FROM position_closure pc
                    JOIN candidates c ON pc.candidate_id = c.candidate_id
                    WHERE pc.status = 'joined' AND pc.job_id IN ({placeholders})
                """), params).mappings().fetchall()
            else:
                result = []


        else:
            flash("You are not authorized to view joined candidates.", "danger")
            return redirect(url_for('login'))

    return render_template("candidate_joined.html", result=result)


@app.route('/profile')
def user_profile():
    if 'username' not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for('login'))

    username = session['username']
    print(username)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                emp_id, username, emp_name, emp_code, gender, phone_num, location,
                designation, department, dept_id, salary, joining_date, role, position_id
            FROM employee
            WHERE username = :username
        """), {'username': username.strip()}).mappings().first()
        print(result)

    if not result:
        flash("Profile not found.", "danger")
        return redirect(url_for('login'))

    return render_template("profile.html", profile=result)





                  # Step 4: Render form with prefilled candidate data
           

            
                            




# Recruiter dashboard route
# @app.route('/add_candidate', methods=['GET','POST'])
# @login_required
# def add_candidate():
      

#     if session['role'].lower() != 'recruiter':
#         flash('Access denied', 'danger')
#         return redirect(url_for('login'))
  
#     try:
#         # Get form data
#         candidate_data = {
#             'candidate_name': request.form.get('candidate_name'),
#             'hr_name': request.form.get('hr_name'),
#             'dept_name': request.form.get('dept_name'),
#             'recruiter_name': request.form.get('recruiter_name'),
#             'recruiter_id': request.form.get('recruiter_id'),
#             'candidate_email': request.form.get('candidate_email'),
#             'candidate_phone': request.form.get('candidate_phone'),
#             'candidate_address': request.form.get('candidate_address'),
#             'candidate_education': request.form.get('candidate_education'),
#             'candidate_skills': request.form.get('candidate_skills'),
#             'candidate_experience': request.form.get('candidate_experience'),
#             'current_company': request.form.get('current_company'),
#             'current_designation': request.form.get('current_designation'),
#             'current_salary': request.form.get('current_salary'),
#             'expected_salary': request.form.get('expected_salary'),
#             'current_location': request.form.get('current_location'),
#             'current_industry': request.form.get('current_industry'),
#             'position': request.form.get('position'),
#             'hod_name': request.form.get('hod_name'),
#             'hod_id': request.form.get('hod_id'),
#             'assigned_date': formated_datetime,
            
#             # 'status': request.form.get('status'),  
#             'job_id': request.form.get('job_id'),
#             'Source': request.form.get('Source'),
            
            
#         }

#         print(candidate_data)  # Add this line to print the candidate data to the console

#          # Print to console for debugging

#         # Connect to database
#         with engine.connect() as connection:
            
#             connection.execute(text('''
#                         INSERT INTO Candidates (
#                             candidate_name, hr_name, dept_name, recruiter_name, 
#                             recruiter_id, candidate_email, candidate_phone, candidate_address, candidate_education, 
#                             candidate_skills, candidate_experience, current_company, current_designation, 
#                             current_salary, expected_salary, current_location, current_industry, position, 
#                             hod_name, assigned_date,job_id,Source,hod_id
#                         ) VALUES (
#                             :candidate_name, :hr_name, :dept_name, :recruiter_name, 
#                             :recruiter_id, :candidate_email, :candidate_phone, :candidate_address,
#                             :candidate_education, :candidate_skills, :candidate_experience,
#                             :current_company, :current_designation, :current_salary,
#                             :expected_salary, :current_location, :current_industry,
#                             :position, :hod_name, :assigned_date,:job_id,:Source,:hod_id
#                         )
#                     '''), {  # ← this comma was missing
#                         'candidate_name': candidate_data['candidate_name'],
#                         'hr_name': candidate_data['hr_name'], 
#                         'dept_name': candidate_data['dept_name'],
#                         'recruiter_name': candidate_data['recruiter_name'],
#                         'recruiter_id': candidate_data['recruiter_id'],
#                         'candidate_email': candidate_data['candidate_email'],
#                         'candidate_phone': candidate_data['candidate_phone'],
#                         'candidate_address': candidate_data['candidate_address'],
#                         'candidate_education': candidate_data['candidate_education'],
#                         'candidate_skills': candidate_data['candidate_skills'],
#                         'candidate_experience': candidate_data['candidate_experience'],
#                         'current_company': candidate_data['current_company'],
#                         'current_designation': candidate_data['current_designation'],
#                         'current_salary': candidate_data['current_salary'],
#                         'expected_salary': candidate_data['expected_salary'],
#                         'current_location': candidate_data['current_location'],
#                         'current_industry': candidate_data['current_industry'],
#                         'position': candidate_data['position'],
#                         'hod_name': candidate_data['hod_name'],
                         
#                         'assigned_date': formated_datetime,
#                         # 'status': candidate_data['status'],
#                         'job_id': candidate_data['job_id'],
#                         'Source': candidate_data['Source'],
#                         'hod_id':candidate_data['hod_id'],
                       

#                     })


#             # connection.execute(insert_query)
#             connection.commit()
#             flash('Candidate added successfully!','success')
#             return redirect(url_for('view_recruiter_dashboard'))

#     except Exception as e:
#         print(f"Error: {str(e)}")
#         flash('An error occurred while adding the candidate', 'error') 
#         return redirect(url_for('view_recruiter_dashboard'))

# @app.route('/recruiter_dashboard/')
# @app.route('/recruiter_dashboard/<recruiter_name>')
# @login_required
# def view_recruiter_dashboard(recruiter_name=None):
#     if recruiter_name is None:
#         recruiter_name = session['username']
      
#     if session['role'] == 'hr':
#         # Map HR usernames to their display names
#         hr_mapping = {
#             'hr1': 'Alice Johnson',
#             'hr2': 'Bob Smith'
#         }
        
#         # Get the HR's display name based on their username
#         hr_display_name = hr_mapping.get(session['username'])
        
#         # Check if the recruiter belongs to this HR using both tables
#         with engine.connect() as connection:
#             # First check HR_Recruiters table
#             data_1 = connection.execute(text('''
#                 SELECT hr.recruiter_id, hr.recruiter_name
#                 FROM HR_Recruiters hr
#                 WHERE hr.hr_name = :hr_display_name 
#                 AND hr.recruiter_name = :recruiter_name
#             '''), {
#                 'hr_display_name': hr_display_name,
#                 'recruiter_name': recruiter_name
#             })

#             recruiter = data_1.fetchone()

#             if not recruiter:
#                 flash('Access denied: Recruiter not found or not assigned to you', 'danger')
#                 return redirect(url_for('hr_dashboard'))
            
#     elif session['role'] == 'recruiter':
#         if session['username'] != recruiter_name:
#             flash('Access denied: You can only view your own dashboard', 'danger')
#             return redirect(url_for('login'))
#     else:
#         flash('Access denied', 'danger')
#         return redirect(url_for('login'))
        
#     with engine.connect() as connection:
#         # Get recruiter's assigned jobs and details
#         data_2 = connection.execute(text('''
#             SELECT ja.recruiter_id, ja.recruiter_email, ja.recruiter_name,
#                    ja.hr_name, d.dept_name, d.hod_name, d.hod_id ,j.position,
#                    ja.status, ja.assigned_status, ja.assigned_date, ja.assigned_by, ja.job_id
#             FROM job_assigned ja
#             LEFT JOIN Departments d ON ja.dept_id = d.dept_id
#             LEFT JOIN jobopening j ON ja.job_id = j.job_id
#             WHERE ja.recruiter_name = :recruiter_name
#         '''), {'recruiter_name': recruiter_name})
        
#         jobs = data_2.fetchall()

#         # Get recruiter details
#         hr_recruiter_data = connection.execute(text('''
#             SELECT * FROM job_assigned
#             WHERE recruiter_name = :recruiter_name
#         '''), {'recruiter_name': recruiter_name})
        
#         hr_recruiters = hr_recruiter_data.fetchall()

        
#         return render_template('view_recruiter_dashboard.html', 
#                             formated_datetime=formated_datetime,
#                             jobs=jobs, 
#                             recruiter_name=recruiter_name,
#                             hr_recruiters=hr_recruiters
#                             )
                            
                            







# @app.route('/Candidates')
# @login_required
# def candidates():
#     if session['role'] != 'recruiter':
#         flash('Access denied', 'danger')
#         return redirect(url_for('login'))
        
#     # Get the logged-in recruiter's name
#     recruiter_name = session['username']
    
#     # Get filter parameters
#     position_filter = request.args.get('position', '')
#     status_filter = request.args.get('status', '')
#     search_query = request.args.get('search', '')
    
#     with engine.connect() as connection:
    
#     # Base query to fetch candidates assigned to this recruiter
#         query = """
#             SELECT candidate_id, candidate_name, hr_name, dept_name, recruiter_name, recruiter_id,
#                 candidate_email, candidate_phone, candidate_address, candidate_education,
#                 candidate_skills, candidate_experience, current_company, current_designation,
#                 current_salary, expected_salary, current_location, current_industry,
#                 position, hod_name, assigned_date, status,job_id,Source,hod_id
#             FROM Candidates
#             WHERE recruiter_name = : recruiter_name
#         """
        
        
#         params = [recruiter_name]
        
       
           
#         # Start with your base query and always include recruiter_name
#         query = "SELECT * FROM Candidates WHERE recruiter_name = :recruiter_name"
#         params = {'recruiter_name': recruiter_name}

#         if position_filter:
#             query += " AND position = :position"
#             params['position'] = position_filter
        
#         if status_filter:
#             query += " AND status = :status"
#             params['status'] = status_filter
           
#         if search_query:
#             query += " AND (candidate_name LIKE :search1 OR candidate_skills LIKE :search2)"
#             params['search1'] = f"%{search_query}%"
#             params['search2'] = f"%{search_query}%"

#         candidates = connection.execute(text(query), params).fetchall()

                        
#         # Get unique positions for filter dropdown
#         data_21=connection.execute(
#             text("""
#                 SELECT DISTINCT position 
#                 FROM Candidates 
#                 WHERE recruiter_name = :recruiter_name AND position IS NOT NULL AND position != ''
#                 ORDER BY position
#             """), {'recruiter_name':recruiter_name})
#         positions = [row[0] for row in data_21.fetchall()]
        
#         # Get unique statuses for filter dropdown
#         data_22=connection.execute(text("""
#                 SELECT DISTINCT status 
#                 FROM Candidates 
#                 WHERE recruiter_name = :recruiter_name AND status IS NOT NULL
#                 ORDER BY status
#             """), {'recruiter_name':recruiter_name})
#         statuses = [row[0] for row in data_22.fetchall()]
            
#         connection.close()
        
#         return render_template('candidates.html', 
#                             candidates=candidates, 
#                             positions=positions, 
#                             statuses=statuses,
#                             current_position=position_filter,
#                             current_status=status_filter,
#                             current_search=search_query)


# @app.route('/submit_position_closure_form', methods=['POST'])
# @login_required
# def submit_position_closure_form():

#     if session['role'] not in ['recruiter']:
#         flash('Access denied', 'danger')
#         return redirect(url_for('candidates'))

#     try:
#         candidate_id = request.form.get('candidate_id')
#         candidate_name = request.form.get('candidate_name')
#         job_id = request.form.get('Job_ID')
#         hr_name = request.form.get('Hr_Name')
#         recruiter_name = request.form.get('Recruiter_Name')
#         recruiter_id = request.form.get('Recruiter_ID')
#         hod_name = request.form.get('Hod_Name')
#         hod_id=request.form.get('hod_id')
#         position = request.form.get('position')
#         dept_name = request.form.get('dept_name')
#         location = request.form.get('location')
#         salary_bracket=request.form.get('salary_bracket')
#         remarks=request.form.get('remarks')
#         offered_salary = request.form.get('offered_salary')
#         joining_bonus = request.form.get('joining_bonus')
#         doj=request.form.get('joining_date')
#         status = 'Candidate Joined'

        
#         with engine.connect() as connection:

#             # Insert into PositionClosure table
#             connection.execute(text('''
#                 INSERT INTO PositionClosure (
#                     candidate_name, job_id, hr_name, recruiter_name, recruiter_id, hod_name, dept_name, 
#                     position, location, salary_bracket, doj, candidate_id, remarks,offered_salary,joining_bonus, status , hod_id
#                 ) VALUES (
#                     :candidate_name, :job_id, :hr_name, :recruiter_name, :recruiter_id, :hod_name, :dept_name, 
#                     :position, :location, :salary_bracket, :doj, :candidate_id, :remarks,:offered_salary,:joining_bonus, :status , :hod_id
#                 )
#             '''), {
#                     'candidate_name': candidate_name,
#                     'job_id': job_id,
#                     'hr_name': hr_name,
#                     'recruiter_name': recruiter_name,
#                     'recruiter_id': recruiter_id,
#                     'hod_name': hod_name,
#                     'hod_id':hod_id,
#                     'dept_name': dept_name,
#                     'position': position,
#                     'location': location,
#                     'salary_bracket': salary_bracket,
#                     'doj': doj,
#                     'candidate_id': candidate_id,
#                     'remarks': remarks,
#                     'offered_salary':offered_salary,
#                     'joining_bonus':joining_bonus,
#                     'status': status
#                  })
#             connection.commit()


#             # Run the UPDATE query
#             connection.execute(text('''
#             UPDATE Candidates
#             SET status = :status
#             WHERE candidate_id = :candidate_id
#             '''), {
#                 'status': status,
#                 'candidate_id': candidate_id
#             })
#             connection.commit()

#             connection.execute(text('''
#             UPDATE jobopening j
#             SET hr_id = (
#                 SELECT hr_id 
#                 FROM PositionClosure 
#                 WHERE job_id = j.job_id
#             ),
#             recruiter_id = (
#                 SELECT recruiter_id
#                 FROM PositionClosure
#                 WHERE job_id = j.job_id
#             )
#             WHERE j.job_id = :job_id
#             '''), {
#                 'job_id': job_id
#             })



#         flash('Position closure successfully recorded!', 'success')
#         return redirect(url_for('candidates')) 

#     except Exception as e:
#         flash(f'Error: {str(e)}', 'error')
#         return redirect(url_for('candidates'))

        
  



# @app.route('/add_candidate_activity', methods=['POST'])
# @login_required
# def add_candidate_activity():
#     if session['role'] not in ['recruiter', 'hr']:
#         flash('Access denied', 'danger')
#         return redirect(url_for('login'))

#     try:
#         with engine.connect() as connection:

#         # Get form data
#             candidate_id = request.form.get('candidate_id')
#             activity_type = request.form.get('activity_type')
#             activity_description = request.form.get('activity_description')
           
#             status = request.form.get('status')
#             remarks=request.form.get('remarks')
            

#             candidate_info=connection.execute(text('''
#             select * from Candidates where candidate_id = :candidate_id
#             '''), {'candidate_id':candidate_id}).mappings().fetchone()

           


#             if not candidate_info:
#                 flash('Candidate not found!', 'error')
#                 return redirect(url_for('candidates'))

#             candidate_name = candidate_info['candidate_name']
#             print(f'Candidate info - {candidate_name}')

#             # Insert into CandidateActivity table
#             connection.execute(text('''insert into candidate_activity(
#                     candidate_name, hr_name, dept_name, recruiter_name, recruiter_id, candidate_email,
#                     candidate_phone, candidate_address, candidate_education, candidate_skills,
#                     candidate_experience, current_company, current_designation, current_salary,
#                     expected_salary, current_location, current_industry, position, job_id, hod_name,
#                     assigned_date, status, remarks, activity_date, activity_description, candidate_id,hod_id
#                     )
#                     values(
#                     :candidate_name, :hr_name, :dept_name, :recruiter_name, :recruiter_id, :candidate_email,
#                     :candidate_phone, :candidate_address, :candidate_education, :candidate_skills,
#                     :candidate_experience, :current_company, :current_designation, :current_salary,
#                     :expected_salary, :current_location, :current_industry, :position, :job_id, :hod_name,
#                     :assigned_date, :status, :remarks, :activity_date, :activity_description, :candidate_id,:hod_id
#                     )
#                     '''), {
#                 'candidate_name': candidate_info['candidate_name'],
#                 'hr_name': candidate_info['hr_name'],       
#                 'dept_name': candidate_info['dept_name'],
#                 'recruiter_name': candidate_info['recruiter_name'],
#                 'recruiter_id': candidate_info['recruiter_id'],
#                 'candidate_email': candidate_info['candidate_email'],
#                 'candidate_phone': candidate_info['candidate_phone'],
#                 'candidate_address': candidate_info['candidate_address'],
#                 'candidate_education': candidate_info['candidate_education'],
#                 'candidate_skills': candidate_info['candidate_skills'],
#                 'candidate_experience': candidate_info['candidate_experience'],
#                 'current_company': candidate_info['current_company'],
#                 'current_designation': candidate_info['current_designation'],
#                 'current_salary': candidate_info['current_salary'],
#                 'expected_salary': candidate_info['expected_salary'],
#                 'current_location': candidate_info['current_location'],
#                 'current_industry': candidate_info['current_industry'],
#                 'position': candidate_info['position'],
#                 'job_id': candidate_info['job_id'],
#                 'hod_name': candidate_info['hod_name'],
#                 'assigned_date': candidate_info['assigned_date'],
#                 'status': status,
#                 'remarks': remarks,
#                 'activity_date': formated_datetime,
#                 'activity_description': activity_description,
#                 'candidate_id': candidate_info['candidate_id'],
#                 'hod_id': candidate_info['hod_id']
#             })

#             connection.commit()

#             flash('Candidate activity added successfully!','success')
#             return redirect(url_for('candidate'))  
            
#     except Exception as e:
#         flash(f'Error adding candidate activity: {str(e)}', 'danger')
#         return redirect(url_for('candidates'))



# @app.route('/view_candidate_activity/<int:candidate_id>', methods=['GET'])
# @login_required
# def view_candidate_activity(candidate_id):
#     if 'user_id' not in session:
#         return redirect(url_for('login'))

#     try:
#         with engine.connect() as conn:
#             # Fetch candidate details
#             candidate_result = conn.execute(
#                 text("SELECT * FROM Candidates WHERE candidate_id = :candidate_id"),
#                 {'candidate_id': candidate_id}
#             )
#             candidate = candidate_result.fetchone()
#             print(candidate)

#             if not candidate:
#                 flash('Candidate not found.', 'danger')
#                 return redirect(url_for('candidates'))

#             # Fetch candidate activities
#             activity_result = conn.execute(
#                 text("SELECT * FROM candidate_activity WHERE candidate_id = :candidate_id"),
#                 {'candidate_id': candidate_id}
#             )
#             activities = activity_result.fetchall()

#             return render_template(
#                 'view_candidate_activity.html',
#                 candidate=candidate,
#                 activities=activities
#             )

#     except Exception as e:
#         flash(f"Database error: {str(e)}", "danger")
#         return render_template('view_candidate_activity.html')


# @app.route('/candidate_joined' , methods=['GET'])
# @login_required
# def candidate_joined():
#     if session['role'] not in ['user', 'recruiter', 'hr']:
#         flash('Access denied', 'danger')
#         return redirect(url_for('login'))

#     with engine.connect() as connection:
#         Username = session['username']
#         if session['role'] == 'user':
#             result = connection.execute(text('SELECT * FROM PositionClosure WHERE hod_name = :hod_name'), {'hod_name': Username})
#         elif session['role'] == 'recruiter':
#             result = connection.execute(text('SELECT * FROM PositionClosure WHERE recruiter_name = :recruiter_name'), {'recruiter_name': Username})
#         elif session['role'] == 'hr':
#             result = connection.execute(text('SELECT * FROM PositionClosure WHERE hr_name = :hr_name'), {'hr_name': Username})
#         else:
#             flash('Invalid Role', 'danger')
#             return redirect(url_for('login'))


#         joined_candidates = result.mappings().fetchall()
#         return render_template('candidate_joined.html', joined_candidates=joined_candidates)       


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)






    
























