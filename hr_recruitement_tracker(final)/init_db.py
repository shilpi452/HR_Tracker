import mysql.connector
from sqlalchemy import create_engine , text 

from sqlalchemy.orm import sessionmaker


server = '193.203.184.158'
database = 'u759228348_smartrecruit'
user_name = 'u759228348_smartrecruit'
password = quote_plus('Smartrecruit@1')  # Encodes @ to %40

class InitDB:
    def get_db_connection():
        server = '193.203.184.158'
        database = 'u759228348_smartrecruit'
        user_name = 'u759228348_smartrecruit'
        password = quote_plus('Smartrecruit@1')  # Encodes @ to %40

        engine = create_engine(
            f"mysql+pymysql://{user_name}:{password}@{server}/{database}",
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False
        )
        return engine




    def db_create():
        engine = get_db_connection()
        
        try:
            with engine.connect() as connection:
                db = connection.execute(text('SHOW DATABASES LIKE :database;'), {'database': database}).mappings().fetchone()
                if db:
                    print(f"✅ Database {database} already exists.")
                    return
                else:
                    print(f"✅ Database {database} does not exist. Creating...")
                    connection.execute(text(f"CREATE DATABASE {database}"))
                    print(f"✅ Database {database} created.")
        except Exception as e:
            print(f"❌ Failed to create database: {e}")


    def table_create_m_roles():
        engine = get_db_connection()
        table_name = 'm_role'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            role_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        )'''
        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")
                sql = f'''INSERT INTO m_role (role_name, created_at) VALUES 
                                    ('Admin', NOW()),
                                    ('HR Manager', NOW()), 
                                    ('Recruiter', NOW()), 
                                    ('HOD', NOW()), 
                                    ('MIS', NOW());'''
        except Exception as e:
            print(f"❌ Failed to create table: {e}")


    def table_create_m_department():
        engine = get_db_connection()
        table_name = 'm_department'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            dept_id INT AUTO_INCREMENT PRIMARY KEY,
            department_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        )'''
        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")
                sql = f'''INSERT INTO m_department (department_name, created_at) VALUES 
                                    ('Marketing', NOW()),
                                    ('MIS', NOW()), 
                                    ('Calling', NOW()), 
                                    ('Digital Marketing', NOW()), 
                                    ('IT', NOW());'''
        except Exception as e:
            print(f"❌ Failed to create table: {e}")
        
    
    def table_create_m_designation():
        engine = get_db_connection()
        table_name = 'm_designation'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            designation_name VARCHAR(255) NOT NULL,
            band VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        )'''
        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")
                sql = f'''INSERT INTO m_designation (designation_name,band, created_at) VALUES 
                                    ('Manager','A1', NOW()),
                                    ('Sr.Executive','B1', NOW()), 
                                    ('Executive','B2', NOW())
                                    ;'''
        except Exception as e:
            print(f"❌ Failed to create table: {e}")

    def table_create_m_status():
        engine = get_db_connection()
        table_name = 'm_status'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            status_name VARCHAR(255) NOT NULL,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        )'''
        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")
                sql = f'''INSERT INTO m_status (status_name, created_at) VALUES  
                                ('Open', NOW()),
                                ('Unassigned', NOW()),
                                ('Assigned', NOW()),
                                ('In-Progress', NOW()),
                                ('Completed', NOW()),
                                ('Closed', NOW()),
                                ('Cancelled', NOW()),
                                ('Rejected', NOW()),
                                ('Withdrawn', NOW()),
                                ('Not Answered', NOW()),
                                ('Left', NOW()),
                                ('On Hold', NOW()),
                                ('Pending', NOW()),
                                ('In Review', NOW()),
                               
                               ;
                            '''


        except Exception as e:
            print(f"❌ Failed to create table: {e}")

    def table_create_m_activity():
        engine = get_db_connection()
        table_name = 'm_activity'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            type VARCHAR(255) NOT NULL,
            job_activity_name varchar(255) NOT NULL,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        )'''
        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")
                sql = f'''INSERT INTO m_status (type,job_activity_name, created_at) VALUES  
                                 ('Candidate','Application Received', NOW()),
                                ('Candidate','Under Initial Review', NOW()),
                                ('Candidate','Qualified for Next Stage', NOW()),
                                ('Candidate','First Round Interview', NOW()),
                                ('Candidate','Second-Round Interview', NOW()),
                                ('Candidate','Final Round', NOW()),
                                ('Candidate','Assessment in Progress', NOW()),
                                ('Candidate','Background Verification', NOW()),
                                ('Candidate','Offer Extended', NOW()),
                                ('Candidate','Offer Accepted', NOW()),
                                ('Candidate','Onboarding Initiated', NOW()),
                                ('Candidate','Candidate Rejected', NOW()),
                                ('Candidate','Candidate Withdrew', NOW()),
                                ('Candidate','Call Not Answered', NOW()),
                                ('Candidate','Candidate Left',NOW()),
                                ('Job','Linkedin',NOW()),
                                ('Job','Naukri',NOW()),
                                ('Job','Monster',NOW()),
                                ('Job','Indeed',NOW()),
                                ('Job','Other',NOW()),
                                ('Job','Referral',NOW());

                                
                            '''


        except Exception as e:
            print(f"❌ Failed to create table: {e}")

    def user_table():
        engine = get_db_connection()
        table_name ='Users'

        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
           
            username VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            role INT NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
        )'''
        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")
                sql = f'''INSERT INTO {table_name} (employee_id,username, password, role,email, created_at) VALUES
                                
                                ('1','admin','admin','admin','admin@mails.com', NOW());
                        '''


        except Exception as e:
            print(f"❌ Failed to create table: {e}")

    def employee_table():
        engine=get_db_connection()
        table_name='employee'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            employee_id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(255) NOT NULL,
            department INT NOT NULL,
            designation INT NOT NULL,           
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")
                

        except Exception as e:
            print(f"❌ Failed to create table: {e}")

    def Candidates():
        engine=get_db_connection()
        table_name='Candidates'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            candidate_id int auto_increment primary key,
            candidate_name varchar(255) not null,
            employee_id int not null,            
            dept_id int not null,            
            candidate_email varchar(255) not null, 
            candidate_phone varchar(255) not null, 
            candidate_address varchar(255) not null, 
            candidate_education varchar(255) not null, 
            candidate_skills varchar(255) not null, 
            candidate_experience varchar(255) not null, 
            current_company varchar(255) not null, 
            current_designation varchar(255) not null, 
            current_salary varchar(255) not null, 
            expected_salary varchar(255) not null, 
            current_location varchar(255) not null, 
            current_industry varchar(255) not null,                          
             assigned_date datetime , 
             status varchar(255) not null, 
             job_id int not null, 
             Source varchar(255) not null
        )'''

        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")    
                

        except Exception as e:
            print(f"❌ Failed to create table: {e}")

  

        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")


        except Exception as e:
            print(f"❌ Failed to create table: {e}")    

    def JobOpenings():
        engine=get_db_connection()
        table_name='JobOpenings'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            job_id int auto_increment primary key, 
            dept_id int not null, 
            employee_id int not null             
            skills varchar(255) not null, 
            experience int not null,           
            status varchar(255) not null, 
            created_date now(), 
            created_by varchar(255) not null
            )'''

        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")


        except Exception as e:
            print(f"❌ Failed to create table: {e}")

    def Job_Assigned():
        engine=get_db_connection()
        table_name='Job_Assigned'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            employee_id int not null,
            job_id int not null, 
            dept_id int not null,
            user_id int not null, 
            status varchar(255) not null,              
            Assigned_status varchar(255) not null, 
            Assigned_date datetime, 
            assigned_by varchar(255) not null, 
            assigned_to varchar(255) not null,
            created_date datetime
           ) '''

        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")


        except Exception as e:
            print(f"❌ Failed to create table: {e}")

        
    def PositionClosure():
        engine=get_db_connection()
        table_name='PositionClosure'
        sql = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            closure_id int auto_increment primary key, 
            candidate_id int not null
             job_id int not null, 
             employee_id int not null,             
             dept_id int not null,              
             location varchar(255) not null, 
             salary_bracket int not null, 
             doj datetime,              
             remarks varchar(255) not null,
             created_date datetime,
        )'''

        try:
            with engine.connect() as connection:
                connection.execute(text(sql))
                print(f"✅ Table {table_name} created.")


        except Exception as e:
            print(f"❌ Failed to create table: {e}")

   
        
                                



    