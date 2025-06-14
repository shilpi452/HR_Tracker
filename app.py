
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

from functools import wraps
import os
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

# Root route to redirect to login
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # role = request.form.get('role')

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
                    return redirect(url_for('view_recruiter_dashboard', recruiter_name=username))
                elif session['role'] == 'hr':
                    return redirect(url_for('hr_dashboard'))  # Fixed HR redirect
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


@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    try:
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
            
        return render_template('admin_dashboard.html',
                            employee_count=total_employees)
                            # jobopening_count=active_jobs,
                            # pending_approvals=pending_approvals)
        
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", 'danger')
        return redirect(url_for('login'))

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
    

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/user_dashboard' , methods=['GET','POST'])
@login_required
def user_dashboard():
    # Get the logged-in user's ID from session
    user_id = session['user_id']
    
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
            
        '''), {'emp_id': session['emp_id']}).fetchall()
        
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
        
    return render_template('user_dashboard.html', 
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
                        emp_id, dept_id, position_id,
                        emp_name, dept_name, position_name,
                        status, assigned_status, description, created_at
                    ) VALUES (
                        :emp_id, :dept_id, :position_id,
                        :emp_name, :dept_name, :position_name,
                        :status, :assigned_status, :description, :created_at
                    )
                '''), {
                    'emp_id': emp_id,
                    'dept_id': dept_id,
                    'position_id': position_id,
                    'emp_name': emp_name,
                    'dept_name': dept_name,
                    'position_name': position_name,
                    'status': status,
                    'assigned_status': assigned_status,
                    'description': description,
                    'created_at': created_at
                })
                conn.commit()
                
                flash('Job submitted successfully!', 'success')
                
                # Get updated job listings to display
                all_job = conn.execute(text('''
                    SELECT j.*, d.dept_name, p.position_name
                    FROM jobopening j
                    JOIN m_dept d ON j.dept_id = d.dept_id
                    JOIN m_position p ON j.position_id = p.position_id
                    ORDER BY j.created_at DESC
                ''')).fetchall()
                
                return render_template('user_dashboard.html',
                                    all_jobs=all_job,
                                    # Include all other necessary template variables
                                    total_jobs=len(all_job),
                                    open_jobs=len([j for j in all_job if j.status == 'Open']),
                                    assigned_jobs=len([j for j in all_job if j.status == 'Assigned']),
                                    closed_jobs=len([j for j in all_job if j.status == 'Closed']),
                                    recent_jobs=all_job[:5] if len(all_job) > 5 else all_job)
                
        except Exception as e:
            flash(f'Error submitting job: {str(e)}', 'danger')
            return redirect(url_for('user_dashboard'))

# Recruiter dashboard route
@app.route('/add_candidate', methods=['GET','POST'])
@login_required
def add_candidate():
      

    if session['role'].lower() != 'recruiter':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
  
    try:
        # Get form data
        candidate_data = {
            'candidate_name': request.form.get('candidate_name'),
            'hr_name': request.form.get('hr_name'),
            'dept_name': request.form.get('dept_name'),
            'recruiter_name': request.form.get('recruiter_name'),
            'recruiter_id': request.form.get('recruiter_id'),
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
            'position': request.form.get('position'),
            'hod_name': request.form.get('hod_name'),
            'hod_id': request.form.get('hod_id'),
            'assigned_date': formated_datetime,
            
            # 'status': request.form.get('status'),  
            'job_id': request.form.get('job_id'),
            'Source': request.form.get('Source'),
            
            
        }

        print(candidate_data)  # Add this line to print the candidate data to the console

         # Print to console for debugging

        # Connect to database
        with engine.connect() as connection:
            
            connection.execute(text('''
                        INSERT INTO Candidates (
                            candidate_name, hr_name, dept_name, recruiter_name, 
                            recruiter_id, candidate_email, candidate_phone, candidate_address, candidate_education, 
                            candidate_skills, candidate_experience, current_company, current_designation, 
                            current_salary, expected_salary, current_location, current_industry, position, 
                            hod_name, assigned_date,job_id,Source,hod_id
                        ) VALUES (
                            :candidate_name, :hr_name, :dept_name, :recruiter_name, 
                            :recruiter_id, :candidate_email, :candidate_phone, :candidate_address,
                            :candidate_education, :candidate_skills, :candidate_experience,
                            :current_company, :current_designation, :current_salary,
                            :expected_salary, :current_location, :current_industry,
                            :position, :hod_name, :assigned_date,:job_id,:Source,:hod_id
                        )
                    '''), {  # ← this comma was missing
                        'candidate_name': candidate_data['candidate_name'],
                        'hr_name': candidate_data['hr_name'], 
                        'dept_name': candidate_data['dept_name'],
                        'recruiter_name': candidate_data['recruiter_name'],
                        'recruiter_id': candidate_data['recruiter_id'],
                        'candidate_email': candidate_data['candidate_email'],
                        'candidate_phone': candidate_data['candidate_phone'],
                        'candidate_address': candidate_data['candidate_address'],
                        'candidate_education': candidate_data['candidate_education'],
                        'candidate_skills': candidate_data['candidate_skills'],
                        'candidate_experience': candidate_data['candidate_experience'],
                        'current_company': candidate_data['current_company'],
                        'current_designation': candidate_data['current_designation'],
                        'current_salary': candidate_data['current_salary'],
                        'expected_salary': candidate_data['expected_salary'],
                        'current_location': candidate_data['current_location'],
                        'current_industry': candidate_data['current_industry'],
                        'position': candidate_data['position'],
                        'hod_name': candidate_data['hod_name'],
                         
                        'assigned_date': formated_datetime,
                        # 'status': candidate_data['status'],
                        'job_id': candidate_data['job_id'],
                        'Source': candidate_data['Source'],
                        'hod_id':candidate_data['hod_id'],
                       

                    })


            # connection.execute(insert_query)
            connection.commit()
            flash('Candidate added successfully!','success')
            return redirect(url_for('view_recruiter_dashboard'))

    except Exception as e:
        print(f"Error: {str(e)}")
        flash('An error occurred while adding the candidate', 'error') 
        return redirect(url_for('view_recruiter_dashboard'))

@app.route('/recruiter_dashboard/')
@app.route('/recruiter_dashboard/<recruiter_name>')
@login_required
def view_recruiter_dashboard(recruiter_name=None):
    if recruiter_name is None:
        recruiter_name = session['username']
      
    if session['role'] == 'hr':
        # Map HR usernames to their display names
        hr_mapping = {
            'hr1': 'Alice Johnson',
            'hr2': 'Bob Smith'
        }
        
        # Get the HR's display name based on their username
        hr_display_name = hr_mapping.get(session['username'])
        
        # Check if the recruiter belongs to this HR using both tables
        with engine.connect() as connection:
            # First check HR_Recruiters table
            data_1 = connection.execute(text('''
                SELECT hr.recruiter_id, hr.recruiter_name
                FROM HR_Recruiters hr
                WHERE hr.hr_name = :hr_display_name 
                AND hr.recruiter_name = :recruiter_name
            '''), {
                'hr_display_name': hr_display_name,
                'recruiter_name': recruiter_name
            })

            recruiter = data_1.fetchone()

            if not recruiter:
                flash('Access denied: Recruiter not found or not assigned to you', 'danger')
                return redirect(url_for('hr_dashboard'))
            
    elif session['role'] == 'recruiter':
        if session['username'] != recruiter_name:
            flash('Access denied: You can only view your own dashboard', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
        
    with engine.connect() as connection:
        # Get recruiter's assigned jobs and details
        data_2 = connection.execute(text('''
            SELECT ja.recruiter_id, ja.recruiter_email, ja.recruiter_name,
                   ja.hr_name, d.dept_name, d.hod_name, d.hod_id ,j.position,
                   ja.status, ja.assigned_status, ja.assigned_date, ja.assigned_by, ja.job_id
            FROM job_assigned ja
            LEFT JOIN Departments d ON ja.dept_id = d.dept_id
            LEFT JOIN jobopening j ON ja.job_id = j.job_id
            WHERE ja.recruiter_name = :recruiter_name
        '''), {'recruiter_name': recruiter_name})
        
        jobs = data_2.fetchall()

        # Get recruiter details
        hr_recruiter_data = connection.execute(text('''
            SELECT * FROM job_assigned
            WHERE recruiter_name = :recruiter_name
        '''), {'recruiter_name': recruiter_name})
        
        hr_recruiters = hr_recruiter_data.fetchall()

        
        return render_template('view_recruiter_dashboard.html', 
                            formated_datetime=formated_datetime,
                            jobs=jobs, 
                            recruiter_name=recruiter_name,
                            hr_recruiters=hr_recruiters
                            )
                            
                            


@app.route('/update_recruiter_details', methods=['POST'])
def update_recruiter_details():
    # Your logic to update recruiter details
    return redirect(url_for('view_recruiter_dashboard'))

# # User dashboard route
# @app.route('/user_dashboard')
# @login_required
# def user_dashboard():
#     if session['role'] != 'user':
#         flash('Access denied', 'danger')
#         return redirect(url_for('login'))

#     # Map usernames to their display names
#     user_mapping = {
#         'a@1234': 'a@1234',
#         'b@1234': 'b@1234',
#         'c@1234': 'c@1234',
#         'd@1234': 'ad@1234'
        
#     }
    
#     current_user = session.get('username')
#     user_display_name = user_mapping.get(current_user)
    
#     if not user_display_name:
#         flash('User not found', 'danger')
#         return redirect(url_for('login'))

#     # Check if trying to access another user's dashboard
#     requested_user = request.args.get('user', current_user)
#     if requested_user != current_user:
#         flash('Access denied: You can only view your own dashboard', 'danger')
#         return redirect(url_for('login'))

#     with engine.connect() as connection:
#         # Get jobs created by current user only
#         user_jobs = connection.execute(text('''
#             SELECT * 
#             FROM jobopening
#             WHERE created_by = :username
#             ORDER BY created_date DESC
#         '''), {'username': current_user})
#         user_jobs = user_jobs.fetchall()
        
#         # Get departments created by current user only
#         hods = connection.execute(text('''
#             SELECT dept_id, hod_id, hod_name, dept_name 
#             FROM Departments 
#             WHERE created_by = :username
#         '''), {'username': current_user})
#         hods = hods.fetchall()
        
#         # Get positions created by current user only
#         positions = connection.execute(text('''
#             SELECT DISTINCT position 
#             FROM jobopening 
#             WHERE created_by = :username
#         '''), {'username': current_user})
#         positions = positions.fetchall()
        
#         # Get user info
#         user_info = connection.execute(text('SELECT * FROM Users WHERE username = :username'), 
#                                      {'username': current_user}).fetchone()
        
#         return render_template('user_dashboard.html', 
#                              hods=hods, 
#                              positions=positions,
#                              user_jobs=user_jobs,
#                              current_user=current_user,
                             
#                              user_info=user_info)

# @app.route('/submit_job_opening', methods=['POST'])
# @login_required
# def submit_job_opening():
#     if session['role'] != 'user':
#         flash('Access denied', 'danger')
#         return redirect(url_for('login'))

#     current_user = session.get('username')
    
#     # Verify user exists in mapping
#     user_mapping = {
#         'a@1234': 'a@1234',
#         'b@1234': 'b@1234',
#         'c@1234': 'c@1234',
#         'd@1234': 'ad@1234',
#         'e@1234': 'e@1234'
#     }
    
#     if current_user not in user_mapping:
#         flash('Invalid user', 'danger')
#         return redirect(url_for('login'))

#     try:
#         with engine.connect() as connection:
#             # First verify if the department belongs to the user
#             dept_id = request.form['dept_id']
#             dept_check = connection.execute(text('''
#                 SELECT dept_id FROM Departments 
#                 WHERE dept_id = :dept_id AND created_by = :username
#             '''), {
#                 'dept_id': dept_id,
#                 'username': current_user
#             }).fetchone()
            
#             if not dept_check:
#                 flash('Access denied: You can only submit jobs for departments you created', 'danger')
#                 return redirect(url_for('user_dashboard'))

#             result = connection.execute(text('''
#                 INSERT INTO jobopening (
#                     dept_id, hod_id, position, skills, 
#                     experience, status, created_by, created_date
#                 )
#                 VALUES (
#                     :dept_id, :hod_id, :position, :skills, 
#                     :experience, :status, :created_by, :created_date
#                 )
#             '''), {
#                 'dept_id': dept_id,
#                 'hod_id': request.form['hod_id'],
#                 'position': request.form['position'],
#                 'skills': request.form['skills'],
#                 'experience': request.form['experience'],
#                 'status': request.form['status'],
#                 'created_by': current_user,
#                 'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#             })

#             connection.commit()
#             flash('Job opening submitted successfully!', 'success')
#             return redirect(url_for('user_dashboard'))
            
#     except Exception as e:
#         flash(f'Error submitting job opening: {str(e)}', 'danger')
#         return redirect(url_for('user_dashboard'))


@app.route('/browse_jobs')
@login_required
def browse_jobs():
    if session['role'] not in ['hr', 'user']:
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    current_user = session.get('username')
    
    with engine.connect() as connection:
        if session['role'] == 'user':
            # For users, show only their created jobs
            data_4 = connection.execute(text('''
                SELECT j.job_id, j.dept_id, j.hod_id, j.position, j.skills, j.experience, j.status, 
                       j.created_date, d.dept_name, j.created_by, hr.hr_id, hr.recruiter_id
                FROM jobopening j
                LEFT JOIN HR_Recruiters hr ON j.job_id = hr.job_id
                LEFT JOIN Departments d ON j.dept_id = d.dept_id
                WHERE j.created_by = :username
                ORDER BY j.created_date DESC
            '''), {'username': current_user})
        else:
            # For HR, show all jobs
            data_4 = connection.execute(text('''
                SELECT j.job_id, j.dept_id, j.hod_id, j.position, j.skills, j.experience, j.status, 
                       j.created_date, d.dept_name, j.created_by, hr.hr_id, hr.recruiter_id
                FROM jobopening j
                LEFT JOIN HR_Recruiters hr ON j.job_id = hr.job_id
                LEFT JOIN Departments d ON j.dept_id = d.dept_id
                ORDER BY j.created_date DESC
            '''))
        jobs = data_4.fetchall()

        

    connection.close()
    return render_template('browse_jobs.html', jobs=jobs, current_user=current_user)



@app.route('/hr_dashboard', methods=['GET'])
@login_required
def hr_dashboard():
    if session['role'] != 'hr':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
    
    
    # Map HR usernames to their display names in HR_Recruiters table
    hr_mapping = {
        'hr1': 'Alice Johnson',
        'hr2': 'Bob Smith'
    }
      
    # Get the HR's display name based on their username
    hr_display_name = hr_mapping.get(session['username'])

    with engine.connect() as connection:
             # Fetch recruiters assigned to this HR only
        data = connection.execute(text('''
                SELECT  hr.recruiter_id, hr.recruiter_name, hr.recruiter_email, 
                count(ja.job_id) as total_jobs
                FROM HR_Recruiters hr
                left join job_assigned ja
                on hr.recruiter_id=ja.recruiter_id
                WHERE hr.hr_name = :hr_name
                group by hr.recruiter_name,hr.recruiter_id,hr.recruiter_email
                order by hr.recruiter_id asc
            '''), {'hr_name': hr_display_name})
        
        recruiters = data.fetchall()

        
        connection.close()
        # engine.close()
        
        return render_template('hr_dashboard.html', 
                            recruiters=recruiters, 
                            username=session['username'])


@app.route('/assign_job', methods=['GET', 'POST'])
def assign_job():
    if request.method == 'POST':
        hr_name = request.form['hr_name']
        hr_email = request.form['hr_email']
        recruiter_name = request.form['recruiter_name']
        recruiter_email = request.form['recruiter_email']
        dept_name = request.form['dept_name']
        hod_name = request.form['hod_name']
        
        recruiter_id = request.form['recruiter_id']
        job_id = request.form['job_id']
        job_position = request.form['job_position']
        status = request.form['status']
        assigned_status = request.form['assigned_status']

        try:
            with engine.begin() as connection:  # Automatically commits or rolls back
                # Get recruiter_id and email
                recruiter_result = connection.execute(text('''
                    SELECT recruiter_id, recruiter_email FROM HR_Recruiters
                    WHERE recruiter_name = :recruiter_name LIMIT 1
                '''), {'recruiter_name': recruiter_name}).fetchone()

                if recruiter_result:
                    recruiter_id, recruiter_email = recruiter_result
                else:
                    flash(f'Recruiter {recruiter_name} not found', 'danger')
                    return redirect(url_for('hr_dashboard'))

                # Get dept_id and hod_id
                dept_result = connection.execute(text('''
                    SELECT dept_id, hod_id FROM Departments
                    WHERE dept_name = :dept_name
                '''), {'dept_name': dept_name}).fetchone()

                if dept_result:
                    dept_id, hod_id = dept_result
                else:
                    flash(f'Department {dept_name} not found', 'danger')
                    return redirect(url_for('hr_dashboard'))

                # Get or insert job_id
                # First try to get job_id from jobopening directly
                
                job_result = connection.execute(text('''
                    SELECT job_id ,position FROM jobopening 
                    WHERE position = :job_position
                    ORDER BY job_id DESC
                    LIMIT 1
                '''), {'job_position': job_position}).fetchone()

                if job_result:
                    job_id = job_result[0]
                else:
                    # Insert new job opening and get the job_id
                    result = connection.execute(text('''
                        INSERT INTO jobopening (position, status, dept_id,created_date)
                        VALUES (:job_position, :status, :dept_id,:created_date)
                        RETURNING job_id
                    '''), {
                        'job_position': job_position,
                        'status': status,
                        'dept_id': dept_id,
                        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    job_id = result.scalar()

                # Insert job assignment
                connection.execute(text('''
                    INSERT INTO job_assigned (
                        hr_name, hr_email, recruiter_name, recruiter_id, recruiter_email,
                        hod_id, position, user_id, dept_id, job_id,
                        status, assigned_status,assigned_date
                    )
                    VALUES (
                        :hr_name, :hr_email, :recruiter_name, :recruiter_id, :recruiter_email,
                        :hod_id, :position, :user_id, :dept_id, :job_id,
                        :status, :assigned_status,:assigned_date
                    )
                '''), {
                    'hr_name': hr_name,
                    'hr_email': hr_email,
                    'recruiter_name': recruiter_name,
                    'recruiter_id': recruiter_id,
                    'recruiter_email': recruiter_email,
                    'hod_id': hod_id,
                    'position': job_position,
                    'user_id': session.get('user_id'),
                    'dept_id': dept_id,
                    'job_id': job_id,
                    'status': status,
                    'assigned_status': assigned_status,
                    'assigned_date':datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
        except Exception as e:
            flash(f'Error assigning job: {str(e)}', 'danger')
            return redirect(url_for('hr_dashboard'))

        
        return redirect(url_for('hr_dashboard'))

    # --- GET METHOD LOGIC BELOW ---

    hr_mapping = {
        'hr1': 'Alice Johnson',
        'hr2': 'Bob Smith'
    }

    hr_display_name = hr_mapping.get(session['username'])

    with engine.connect() as connection:
        # Fetch HR details
        hrs = connection.execute(text('''
            SELECT DISTINCT hr_name, hr_email FROM HR_Recruiters
            WHERE hr_name = :hr_name
            group by hr_name
        '''), {'hr_name': hr_display_name}).fetchall()

        # Fetch recruiters (safe GROUP BY)
        recruiters = connection.execute(text('''
            SELECT recruiter_name, recruiter_id, recruiter_email, hr_name
            FROM HR_Recruiters
            WHERE hr_name = :hr_name
            group by recruiter_name
        '''), {'hr_name': hr_display_name}).fetchall()

        # Fetch departments
        departments = connection.execute(text('''
            SELECT DISTINCT dept_name, hod_name FROM Departments
        ''')).fetchall()

        # Fetch job positions
        jobs = connection.execute(text('''
            SELECT DISTINCT j.position,j.job_id,j.status,j.created_date
             FROM jobopening j
             where j.status='open'
             order by j.created_date asc
             
            
        ''')).fetchall()

    return render_template('assign_job.html',
                           hrs=hrs,
                           recruiters=recruiters,
                           departments=departments,
                           jobs=jobs)


@app.route('/job_assigned_table_page')
@login_required
def job_assigned_table_page():
    hr_filter = request.args.get('hr_name')
    recruiter_filter = request.args.get('recruiter_name')
    dept_filter = request.args.get('dept_name')

    hr_mapping = {
        'hr1': 'Alice Johnson',
        'hr2': 'Bob Smith'
    }
    logged_in_hr = hr_mapping.get(session['username'])

    with engine.connect() as connection:
        # Start building the query
        base_query = '''
            SELECT 
                ja.hr_id,
                ja.hr_name,
                ja.recruiter_name,
                ja.recruiter_id,
                ja.recruiter_email,
                d.dept_name,
                j.position as job_position,
                ja.status,
                ja.assigned_status,
                d.hod_name,
                d.hod_id,
                ja.assigned_date,
                
                ja.recruiter_id as assignment_id,
                j.job_id
            FROM job_assigned ja
            INNER JOIN Departments d ON ja.dept_id = d.dept_id
            INNER JOIN jobopening j ON ja.job_id = j.job_id
            WHERE ja.assigned_status IS NOT NULL
              AND ja.hr_name = :logged_in_hr
        '''

        params = {'logged_in_hr': logged_in_hr}

        if recruiter_filter:
            base_query += ' AND ja.recruiter_name = :recruiter_name'
            params['recruiter_name'] = recruiter_filter
        if dept_filter:
            base_query += ' AND d.dept_name = :dept_name'
            params['dept_name'] = dept_filter

        base_query += ' ORDER BY ja.assigned_date DESC'

        assignments = connection.execute(text(base_query), params).fetchall()

        # Fetch filter dropdown values
        hrs = [row[0] for row in connection.execute(text('''
            SELECT DISTINCT hr_name 
            FROM job_assigned  
            WHERE hr_name = :logged_in_hr 
            ORDER BY hr_name
        '''), {'logged_in_hr': logged_in_hr})]

        recruiters = [row[0] for row in connection.execute(text('''
            SELECT DISTINCT recruiter_name 
            FROM job_assigned 
            WHERE hr_name = :logged_in_hr 
            ORDER BY recruiter_name
        '''), {'logged_in_hr': logged_in_hr})]

        departments = [row[0] for row in connection.execute(text('''
            SELECT DISTINCT d.dept_name 
            FROM Departments d
            INNER JOIN job_assigned ja ON d.dept_id = ja.dept_id
            WHERE ja.hr_name = :logged_in_hr
            ORDER BY d.dept_name
        '''), {'logged_in_hr': logged_in_hr})]

        jobs = [row[0] for row in connection.execute(text(
            'SELECT DISTINCT position FROM jobopening ORDER BY position'))]

    form_data = [{
        'hr_id': row[0],
        'hr_name': row[1],
        'recruiter_name': row[2],
        'recruiter_id': row[3],
        'recruiter_email': row[4],
        'dept_name': row[5],
        'job_position': row[6],
        'status': row[7],
        'assigned_status': row[8],
        'hod_name': row[9],
        'hod_id': row[10],
        'assigned_date':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        
        'assignment_id': row[11],
        'job_id': row[12]
    } for row in assignments]

    return render_template('job_assigned_table_page.html', 
                           form_data=form_data,
                           hrs=hrs,
                           recruiters=recruiters,
                           departments=departments,
                           jobs=jobs,
                           current_filters={
                               'hr_name': hr_filter,
                               'recruiter_name': recruiter_filter,
                               'dept_name': dept_filter
                           })

@app.route('/delete_assignment/<int:job_id>', methods=['POST'])
def delete_assignment(job_id):
    try:
        with engine.connect() as connection:
            connection.execute(
                text('DELETE FROM job_assigned WHERE job_id = :job_id'),
                {'job_id': job_id}
            )
            connection.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/edit_job_assignment/<int:job_id>', methods=['POST'])
@login_required
def edit_job_assignment(job_id):
    if session['role'] != 'hr':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        with engine.connect() as connection:
            # Update job assignment details
            new_recruiter_name = request.form.get('recruiter_name')
            new_dept_name = request.form.get('dept_name')
            new_job_position = request.form.get('job_position')

            connection.execute(text('''
                UPDATE job_assigned ja
                SET recruiter_name = :new_recruiter_name, 
                    dept_id = (SELECT dept_id FROM departments WHERE dept_name = :new_dept_name),
                    job_id = (SELECT job_id FROM jobopening WHERE position = :new_job_position)
                WHERE job_id = :job_id
            '''), {
                'new_recruiter_name': new_recruiter_name, 
                'new_dept_name': new_dept_name,
                'new_job_position': new_job_position, 
                'job_id': job_id
            })

            connection.commit()
            return jsonify({'success': True, 'message': 'Assignment updated successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500





@app.route('/add_job_position', methods=['POST'])
@login_required
def add_job_position():
    if session['role'] != 'hr':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
        
    data = request.get_json()
    position = data.get('position')
    skills = data.get('skills')
    experience = data.get('experience')
    
    if not all([position, skills, experience]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
    try:
        with engine.conect() as connection:
        
        # Insert new job position
            data_19=connection.execute(text('''
                INSERT INTO jobopening (position, skills, experience, status,created_date)
                VALUES (:position, :skills, :experience, 'Open',:created_date)
            ''', {'position':position, 'skills':skills, 'experience':experience}))
            
            connection.close()
            
            return jsonify({'success': True, 'message': 'Job position added successfully'})
            
    except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    finally:
            connection.close()
    return redirect(url_for('user_dashboard'))

@app.route('/submit_department', methods=['POST'])
@login_required
def submit_department():
    if session['role'] != 'user':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    current_user = session.get('username')
    
    # Verify user exists in mapping
    user_mapping = {
        'a@1234': 'a@1234',
        'b@1234': 'b@1234',
        'c@1234': 'c@1234',
        'd@1234': 'ad@1234',
        'e@1234': 'e@1234'
    }
    
    if current_user not in user_mapping:
        flash('Invalid user', 'danger')
        return redirect(url_for('login'))

    try:
        with engine.connect() as connection:
            # Check if department name already exists for this user
            dept_name = request.form['dept_name']
            existing_dept = connection.execute(text('''
                SELECT dept_id FROM Departments 
                WHERE dept_name = :dept_name AND created_by = :username
            '''), {
                'dept_name': dept_name,
                'username': current_user
            }).fetchone()
            
            if existing_dept:
                flash('Department with this name already exists', 'danger')
                return redirect(url_for('user_dashboard'))

            result = connection.execute(text('''
                INSERT INTO Departments (
                    dept_name, hod_id, hod_name, created_by, created_date
                )
                VALUES (
                    :dept_name, :hod_id, :hod_name, :created_by, :created_date
                )
            '''), {
                'dept_name': dept_name,
                'hod_id': request.form['hod_id'],
                'hod_name': request.form['hod_name'],
                'created_by': current_user,
                'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            connection.commit()
            flash('Department submitted successfully!', 'success')
            return redirect(url_for('user_dashboard'))
            
    except Exception as e:
        flash(f'Error submitting department: {str(e)}', 'danger')
        return redirect(url_for('user_dashboard'))

@app.route('/edit_department', methods=['POST'])
@login_required
def edit_department():
    try:
        # Get form data
        dept_name = request.form.get('dept_name')
        hod_id = request.form.get('hod_id')
        hod_name = request.form.get('hod_name')
        
        # Validate required fields
        if not all([dept_name, hod_id, hod_name]):
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        # Update department in database
        with engine.connect() as connection:
            # First check if department exists
            result = connection.execute(
                text("SELECT dept_id FROM Departments WHERE hod_id = :hod_id"),
                {"hod_id": hod_id}
            ).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Department not found'})
            
            # Update the department details
            connection.execute(
                text("UPDATE Departments SET dept_name = :dept_name, hod_name = :hod_name "
                     "WHERE hod_id = :hod_id"),
                {
                    "dept_name": dept_name,
                    "hod_name": hod_name,
                    "hod_id": hod_id
                }
            )
            
            connection.commit()
            
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error updating department: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update department'})




        

@app.route('/Candidates')
@login_required
def candidates():
    if session['role'] != 'recruiter':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
        
    # Get the logged-in recruiter's name
    recruiter_name = session['username']
    
    # Get filter parameters
    position_filter = request.args.get('position', '')
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    
    with engine.connect() as connection:
    
    # Base query to fetch candidates assigned to this recruiter
        query = """
            SELECT candidate_id, candidate_name, hr_name, dept_name, recruiter_name, recruiter_id,
                candidate_email, candidate_phone, candidate_address, candidate_education,
                candidate_skills, candidate_experience, current_company, current_designation,
                current_salary, expected_salary, current_location, current_industry,
                position, hod_name, assigned_date, status,job_id,Source,hod_id
            FROM Candidates
            WHERE recruiter_name = : recruiter_name
        """
        
        
        params = [recruiter_name]
        
       
           
        # Start with your base query and always include recruiter_name
        query = "SELECT * FROM Candidates WHERE recruiter_name = :recruiter_name"
        params = {'recruiter_name': recruiter_name}

        if position_filter:
            query += " AND position = :position"
            params['position'] = position_filter
        
        if status_filter:
            query += " AND status = :status"
            params['status'] = status_filter
           
        if search_query:
            query += " AND (candidate_name LIKE :search1 OR candidate_skills LIKE :search2)"
            params['search1'] = f"%{search_query}%"
            params['search2'] = f"%{search_query}%"

        candidates = connection.execute(text(query), params).fetchall()

                        
        # Get unique positions for filter dropdown
        data_21=connection.execute(
            text("""
                SELECT DISTINCT position 
                FROM Candidates 
                WHERE recruiter_name = :recruiter_name AND position IS NOT NULL AND position != ''
                ORDER BY position
            """), {'recruiter_name':recruiter_name})
        positions = [row[0] for row in data_21.fetchall()]
        
        # Get unique statuses for filter dropdown
        data_22=connection.execute(text("""
                SELECT DISTINCT status 
                FROM Candidates 
                WHERE recruiter_name = :recruiter_name AND status IS NOT NULL
                ORDER BY status
            """), {'recruiter_name':recruiter_name})
        statuses = [row[0] for row in data_22.fetchall()]
            
        connection.close()
        
        return render_template('candidates.html', 
                            candidates=candidates, 
                            positions=positions, 
                            statuses=statuses,
                            current_position=position_filter,
                            current_status=status_filter,
                            current_search=search_query)


@app.route('/submit_position_closure_form', methods=['POST'])
@login_required
def submit_position_closure_form():

    if session['role'] not in ['recruiter']:
        flash('Access denied', 'danger')
        return redirect(url_for('candidates'))

    try:
        candidate_id = request.form.get('candidate_id')
        candidate_name = request.form.get('candidate_name')
        job_id = request.form.get('Job_ID')
        hr_name = request.form.get('Hr_Name')
        recruiter_name = request.form.get('Recruiter_Name')
        recruiter_id = request.form.get('Recruiter_ID')
        hod_name = request.form.get('Hod_Name')
        hod_id=request.form.get('hod_id')
        position = request.form.get('position')
        dept_name = request.form.get('dept_name')
        location = request.form.get('location')
        salary_bracket=request.form.get('salary_bracket')
        remarks=request.form.get('remarks')
        offered_salary = request.form.get('offered_salary')
        joining_bonus = request.form.get('joining_bonus')
        doj=request.form.get('joining_date')
        status = 'Candidate Joined'

        
        with engine.connect() as connection:

            # Insert into PositionClosure table
            connection.execute(text('''
                INSERT INTO PositionClosure (
                    candidate_name, job_id, hr_name, recruiter_name, recruiter_id, hod_name, dept_name, 
                    position, location, salary_bracket, doj, candidate_id, remarks,offered_salary,joining_bonus, status , hod_id
                ) VALUES (
                    :candidate_name, :job_id, :hr_name, :recruiter_name, :recruiter_id, :hod_name, :dept_name, 
                    :position, :location, :salary_bracket, :doj, :candidate_id, :remarks,:offered_salary,:joining_bonus, :status , :hod_id
                )
            '''), {
                    'candidate_name': candidate_name,
                    'job_id': job_id,
                    'hr_name': hr_name,
                    'recruiter_name': recruiter_name,
                    'recruiter_id': recruiter_id,
                    'hod_name': hod_name,
                    'hod_id':hod_id,
                    'dept_name': dept_name,
                    'position': position,
                    'location': location,
                    'salary_bracket': salary_bracket,
                    'doj': doj,
                    'candidate_id': candidate_id,
                    'remarks': remarks,
                    'offered_salary':offered_salary,
                    'joining_bonus':joining_bonus,
                    'status': status
                 })
            connection.commit()


            # Run the UPDATE query
            connection.execute(text('''
            UPDATE Candidates
            SET status = :status
            WHERE candidate_id = :candidate_id
            '''), {
                'status': status,
                'candidate_id': candidate_id
            })
            connection.commit()

            connection.execute(text('''
            UPDATE jobopening j
            SET hr_id = (
                SELECT hr_id 
                FROM PositionClosure 
                WHERE job_id = j.job_id
            ),
            recruiter_id = (
                SELECT recruiter_id
                FROM PositionClosure
                WHERE job_id = j.job_id
            )
            WHERE j.job_id = :job_id
            '''), {
                'job_id': job_id
            })



        flash('Position closure successfully recorded!', 'success')
        return redirect(url_for('candidates')) 

    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('candidates'))

        
  

@app.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    if session['role'] not in ['hr','user']:
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    current_user = session.get('username')
    
    try:
        with engine.connect() as connection:
            # First check if the job belongs to the current user
            job_check = connection.execute(text('''
                SELECT job_id FROM jobopening 
                WHERE job_id = :job_id AND created_by = :username
            '''), {
                'job_id': job_id,
                'username': current_user
            }).fetchone()
            
            if not job_check:
                
                return redirect(url_for('hr_dashboard'))

            # Delete the job
            connection.execute(text('DELETE FROM jobopening WHERE job_id = :job_id'), {'job_id': job_id})
            connection.commit()
            
            flash('Job opening deleted successfully!', 'success')
            return redirect(url_for('browse_jobs'))
            
    except Exception as e:
        flash(f'Error deleting job opening: {str(e)}', 'danger')
        return redirect(url_for('browse_jobs'))


@app.route('/add_candidate_activity', methods=['POST'])
@login_required
def add_candidate_activity():
    if session['role'] not in ['recruiter', 'hr']:
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    try:
        with engine.connect() as connection:

        # Get form data
            candidate_id = request.form.get('candidate_id')
            activity_type = request.form.get('activity_type')
            activity_description = request.form.get('activity_description')
           
            status = request.form.get('status')
            remarks=request.form.get('remarks')
            

            candidate_info=connection.execute(text('''
            select * from Candidates where candidate_id = :candidate_id
            '''), {'candidate_id':candidate_id}).mappings().fetchone()

           


            if not candidate_info:
                flash('Candidate not found!', 'error')
                return redirect(url_for('candidates'))

            candidate_name = candidate_info['candidate_name']
            print(f'Candidate info - {candidate_name}')

            # Insert into CandidateActivity table
            connection.execute(text('''insert into candidate_activity(
                    candidate_name, hr_name, dept_name, recruiter_name, recruiter_id, candidate_email,
                    candidate_phone, candidate_address, candidate_education, candidate_skills,
                    candidate_experience, current_company, current_designation, current_salary,
                    expected_salary, current_location, current_industry, position, job_id, hod_name,
                    assigned_date, status, remarks, activity_date, activity_description, candidate_id,hod_id
                    )
                    values(
                    :candidate_name, :hr_name, :dept_name, :recruiter_name, :recruiter_id, :candidate_email,
                    :candidate_phone, :candidate_address, :candidate_education, :candidate_skills,
                    :candidate_experience, :current_company, :current_designation, :current_salary,
                    :expected_salary, :current_location, :current_industry, :position, :job_id, :hod_name,
                    :assigned_date, :status, :remarks, :activity_date, :activity_description, :candidate_id,:hod_id
                    )
                    '''), {
                'candidate_name': candidate_info['candidate_name'],
                'hr_name': candidate_info['hr_name'],       
                'dept_name': candidate_info['dept_name'],
                'recruiter_name': candidate_info['recruiter_name'],
                'recruiter_id': candidate_info['recruiter_id'],
                'candidate_email': candidate_info['candidate_email'],
                'candidate_phone': candidate_info['candidate_phone'],
                'candidate_address': candidate_info['candidate_address'],
                'candidate_education': candidate_info['candidate_education'],
                'candidate_skills': candidate_info['candidate_skills'],
                'candidate_experience': candidate_info['candidate_experience'],
                'current_company': candidate_info['current_company'],
                'current_designation': candidate_info['current_designation'],
                'current_salary': candidate_info['current_salary'],
                'expected_salary': candidate_info['expected_salary'],
                'current_location': candidate_info['current_location'],
                'current_industry': candidate_info['current_industry'],
                'position': candidate_info['position'],
                'job_id': candidate_info['job_id'],
                'hod_name': candidate_info['hod_name'],
                'assigned_date': candidate_info['assigned_date'],
                'status': status,
                'remarks': remarks,
                'activity_date': formated_datetime,
                'activity_description': activity_description,
                'candidate_id': candidate_info['candidate_id'],
                'hod_id': candidate_info['hod_id']
            })

            connection.commit()

            flash('Candidate activity added successfully!','success')
            return redirect(url_for('candidate'))  
            
    except Exception as e:
        flash(f'Error adding candidate activity: {str(e)}', 'danger')
        return redirect(url_for('candidates'))



@app.route('/view_candidate_activity/<int:candidate_id>', methods=['GET'])
@login_required
def view_candidate_activity(candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        with engine.connect() as conn:
            # Fetch candidate details
            candidate_result = conn.execute(
                text("SELECT * FROM Candidates WHERE candidate_id = :candidate_id"),
                {'candidate_id': candidate_id}
            )
            candidate = candidate_result.fetchone()
            print(candidate)

            if not candidate:
                flash('Candidate not found.', 'danger')
                return redirect(url_for('candidates'))

            # Fetch candidate activities
            activity_result = conn.execute(
                text("SELECT * FROM candidate_activity WHERE candidate_id = :candidate_id"),
                {'candidate_id': candidate_id}
            )
            activities = activity_result.fetchall()

            return render_template(
                'view_candidate_activity.html',
                candidate=candidate,
                activities=activities
            )

    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")
        return render_template('view_candidate_activity.html')


@app.route('/candidate_joined' , methods=['GET'])
@login_required
def candidate_joined():
    if session['role'] not in ['user', 'recruiter', 'hr']:
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    with engine.connect() as connection:
        Username = session['username']
        if session['role'] == 'user':
            result = connection.execute(text('SELECT * FROM PositionClosure WHERE hod_name = :hod_name'), {'hod_name': Username})
        elif session['role'] == 'recruiter':
            result = connection.execute(text('SELECT * FROM PositionClosure WHERE recruiter_name = :recruiter_name'), {'recruiter_name': Username})
        elif session['role'] == 'hr':
            result = connection.execute(text('SELECT * FROM PositionClosure WHERE hr_name = :hr_name'), {'hr_name': Username})
        else:
            flash('Invalid Role', 'danger')
            return redirect(url_for('login'))


        joined_candidates = result.mappings().fetchall()
        return render_template('candidate_joined.html', joined_candidates=joined_candidates)       


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)






    
























