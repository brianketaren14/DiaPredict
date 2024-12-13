from flask import Flask, render_template, request, jsonify, redirect, session, flash
import pickle
import mysql.connector
from datetime import datetime
import hashlib
import secrets
import os

home = os.getcwd()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)



# Konfigurasi koneksi ke database MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'diapredict'
}

model = pickle.load(open('model/gb_hyper_model.pkl', 'rb'))
scalar = pickle.load(open('model/scalar.pkl', 'rb'))

def encrypt_password(password):
    return hashlib.md5(password.encode()).hexdigest()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' not in session:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            encrypted_password = encrypt_password(password)

            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            query = "SELECT user_id FROM users WHERE username = %s AND password = %s"
            cursor.execute(query, (username, encrypted_password))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                session['user_id'] = user['user_id']
                return redirect('/')
            else:
                return render_template('login.html', status_login=False)
        else:
            return render_template('login.html', status_login="")
    else:
        return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session:
        if request.method == 'POST':
            nama = request.form['nama']
            tanggal_lahir = request.form['tanggal_lahir']
            username = request.form['username']
            password = request.form['password']
            alamat = request.form['alamat']
            encrypted_password = encrypt_password(password)

            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            query_select = "SELECT username FROM users WHERE username = %s"
            cursor.execute(query_select, (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            # kalo usernam sudah dipakai sebelumnya tampilkan register status gagal
            if user:
                return render_template('register.html', register_status=False)

            else:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                query_insert = "INSERT INTO users (nama, tanggal_lahir, alamat, username, password) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query_insert, (nama, tanggal_lahir, alamat, username, encrypted_password))
                conn.commit()
                cursor.close()
                conn.close()

                return render_template('register.html', register_status=True)
        else:
            return render_template('register.html', register_status="")
    else:
        return redirect('/')


@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        if request.method == 'POST':
            user_id = session['user_id']
            nama = request.form['nama']
            umur = int(request.form['umur'])
            DPF = float(request.form['DPF'])
            kehamilan = int(request.form['kehamilan'])
            glucose = float(request.form['glucose'])
            bloodpressure = float(request.form['bloodpressure'])
            ketebalankulit = float(request.form['ketebalankulit'])
            insulin = float(request.form['insulin'])
            BMI = float(request.form['BMI'])

            arr = scalar.transform([[kehamilan, glucose, bloodpressure, ketebalankulit, insulin, BMI, DPF, umur]])
            hasil_prediksi = model.predict(arr)


            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO predict (user_id, Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, prediksi) VALUES ({user_id}, {kehamilan}, {glucose}, {bloodpressure}, {ketebalankulit}, {insulin}, {BMI}, {DPF}, {umur}, {hasil_prediksi[0]})")
            conn.commit()
            cursor.close()
            conn.close()

            return render_template('index.html', nama=nama, hasil_prediksi=hasil_prediksi, umur=umur)

        hasil_prediksi = ""
        user_id = session['user_id']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT nama, tanggal_lahir FROM users WHERE user_id = {user_id}")
        users = cursor.fetchall()
        cursor.close()
        conn.close()

        nama = users[0]['nama']
        tanggal_lahir = users[0]['tanggal_lahir']
        tanggal_sekarang = datetime.now()
        umur = tanggal_sekarang.year - tanggal_lahir.year
        if (tanggal_sekarang.month, tanggal_sekarang.day) < (tanggal_lahir.month, tanggal_lahir.day):
            umur -= 1

        return render_template('index.html', hasil_prediksi=hasil_prediksi, nama=nama, umur=umur)



@app.route('/about')
def about():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        return render_template('about.html')

@app.route('/reset')
def reset():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        return redirect('/')



@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT nama, username, alamat, tanggal_lahir FROM users WHERE user_id = {user_id}")
        users = cursor.fetchone()
        cursor.close()
        conn.close()

        return render_template('account.html', users = users, update_account_status="", status_ubah_password="")

@app.route('/update_account', methods=['POST'])
def update_account():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        update_account_status = ""
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            nama = request.form['nama']
            alamat = request.form['alamat']
            tanggal_lahir = request.form['tanggal_lahir']

            cursor.execute(f"UPDATE users SET nama = '{nama}', alamat = '{alamat}', tanggal_lahir = '{tanggal_lahir}' WHERE user_id = {user_id}")
            conn.commit()
            update_account_status = True

            cursor.execute(f"SELECT nama, username, alamat, tanggal_lahir FROM users WHERE user_id = {user_id}")
            users = cursor.fetchone()
            cursor.close()
            conn.close()
            return render_template('account.html', users = users, update_account_status=update_account_status)

@app.route('/edit_username', methods = ['GET', 'POST'])
def edit_username():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        update_username_status = ""

        if request.method == 'POST':
            username = request.form['username']
            cursor.execute(f"SELECT username FROM users WHERE username = '{username}'")
            username_data = cursor.fetchone()
            print(username_data)

            if username_data:
                update_username_status = False

            else:
                cursor.execute(f"UPDATE users SET username = '{username}' WHERE user_id = {user_id}")
                conn.commit()
                update_username_status = True

        cursor.execute(f"SELECT username, nama, alamat, tanggal_lahir FROM users WHERE user_id = {user_id}")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('account.html',  users = users[0], update_username_status=update_username_status)

@app.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        if request.method == 'POST':
            user_id = session['user_id']
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SELECT nama, username, alamat, tanggal_lahir FROM users WHERE user_id = {user_id}")
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            update_account_status = ""

            old_password = request.form['password_lama']
            new_password = request.form['password_baru']
            confirm_password = request.form['confirm_password']

            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            query = f"SELECT password FROM users WHERE user_id = {user_id} AND password = '{encrypt_password(old_password)}'"
            cursor.execute(query)
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                if new_password != confirm_password:
                    return render_template('account.html', users = users[0], update_account_status=update_account_status, status_ubah_password=False)
                elif new_password == confirm_password:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    cursor.execute(f"UPDATE users SET password = '{encrypt_password(new_password)}' WHERE user_id = {user_id}")
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return render_template('account.html',  users = users[0], update_account_status=update_account_status, status_ubah_password=True)
            else:
                return render_template('account.html', users = users[0], update_account_status=update_account_status, status_ubah_password=False)

@app.route('/perkembangan')
def perkembangan():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT predict_id, Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, prediksi, waktu_predict  FROM predict WHERE user_id = {user_id}")
        predicted = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('perkembangan.html', predicted=predicted)

@app.route('/delete_perkembangan/<int:predict_id>', methods=['GET', 'POST'])
def delete_perkembangan(predict_id):
    if 'user_id' not in session:
        return redirect('/login')
    else:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM predict WHERE predict_id = %s", (predict_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Data berhasil dihapus!')
        return redirect('/perkembangan')

@app.route('/edit_perkembangan/<int:predict_id>', methods=['GET', 'POST'])
def edit_perkembangan(predict_id):
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        edit_perkembangan_status = ""
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            umur = int(request.form['umur'])
            DPF = float(request.form['DPF'])
            kehamilan = int(request.form['kehamilan'])
            glucose = float(request.form['glucose'])
            bloodpressure = float(request.form['bloodpressure'])
            ketebalankulit = float(request.form['ketebalankulit'])
            insulin = float(request.form['insulin'])
            BMI = float(request.form['BMI'])

            arr = scalar.transform([[kehamilan, glucose, bloodpressure, ketebalankulit, insulin, BMI, DPF, umur]])
            hasil_prediksi = model.predict(arr)

            cursor.execute(f"UPDATE predict SET Pregnancies = {kehamilan}, Glucose = {glucose}, BloodPressure = {bloodpressure}, SkinThickness = {ketebalankulit}, Insulin = {insulin}, BMI = {BMI}, DiabetesPedigreeFunction = {DPF}, prediksi = {hasil_prediksi[0]} WHERE predict_id = {predict_id};")
            conn.commit()
            edit_perkembangan_status = True


        query = f"SELECT users.nama, predict.age, predict.Pregnancies, predict.Glucose, predict.BloodPressure, predict.SkinThickness, predict.Insulin, predict.BMI, predict.DiabetesPedigreeFunction FROM predict INNER JOIN users ON predict.user_id = users.user_id WHERE predict_id = {predict_id};"
        cursor.execute(query)
        data_perkembangan = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_perkembangan.html', data_perkembangan=data_perkembangan, edit_perkembangan_status=edit_perkembangan_status)



# function mendapatkan data prediksi dan diubah menjadi json untuk ditampilkan ke plot
def get_data(column, user_id):
    # Connect to the database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Query the database
    cursor.execute(f"SELECT waktu_predict, {column} FROM predict WHERE user_id = {user_id}")
    rows = cursor.fetchall()

    # Format data for Google Charts
    data = [["waktu_predict", f"{column}"]]  # Correct header format as two separate columns
    data.extend(rows)

    cursor.close()
    conn.close()

    return jsonify(data)  # Send data as JSON to the frontend

@app.route('/get_pregnancies_data')
def get_pregnancies_data():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        return get_data('Pregnancies', user_id)

@app.route('/get_glucose_data')
def get_glucose_data():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        return get_data('Glucose', user_id)

@app.route('/get_BloodPressure_data')
def get_BloodPressure_data():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        return get_data('BloodPressure', user_id)

@app.route('/get_SkinThickness_data')
def get_SkinThickness_data():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        return get_data('SkinThickness', user_id)

@app.route('/get_Insulin_data')
def get_Insulin_data():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        return get_data('Insulin', user_id)

@app.route('/get_BMI_data')
def get_BMI_data():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        return get_data('BMI', user_id)

@app.route('/get_DPF_data')
def get_DPF_data():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        return get_data('DiabetesPedigreeFunction', user_id)

@app.route('/get_prediksi_data')
def get_prediksi_data():
    if 'user_id' not in session:
        return redirect('/login')
    else:
        user_id = session['user_id']
        return get_data('prediksi', user_id)

@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if 'admin_id' not in session:
        if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']

                encrypted_password = encrypt_password(password)

                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor(dictionary=True)

                query = "SELECT admin_id FROM admin WHERE username = %s AND password = %s"
                cursor.execute(query, (username, encrypted_password))
                user = cursor.fetchone()

                cursor.close()
                conn.close()

                if user:
                    session['admin_id'] = user['admin_id']
                    return redirect('/admin')
                else:
                    return render_template('login_admin.html', status_login=False)
        else:
            return render_template('login_admin.html', status_login="")
    else:
        return redirect('/admin')

@app.route('/admin')
def admin():
    if 'admin_id' not in session:
        return redirect('/login_admin')
    else:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM predict")
        predicted = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin.html', predicted=predicted)

@app.route('/delete_predict/<int:predict_id>', methods=['GET', 'POST'])
def delete_predict(predict_id):
    if 'admin_id' not in session:
        return redirect('/login_admin')
    else:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM predict WHERE predict_id = %s", (predict_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Data berhasil dihapus!')
        return redirect('/admin')

@app.route('/edit_predict/<int:predict_id>', methods=['GET', 'POST'])
def edit_predict(predict_id):
    if 'admin_id' not in session:
        return redirect('/login_admin')
    else:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        edit_predicted_status = ""
        if request.method == 'POST':
            umur = int(request.form['umur'])
            DPF = float(request.form['DPF'])
            kehamilan = int(request.form['kehamilan'])
            glucose = float(request.form['glucose'])
            bloodpressure = float(request.form['bloodpressure'])
            ketebalankulit = float(request.form['ketebalankulit'])
            insulin = float(request.form['insulin'])
            BMI = float(request.form['BMI'])

            arr = scalar.transform([[kehamilan, glucose, bloodpressure, ketebalankulit, insulin, BMI, DPF, umur]])
            hasil_prediksi = model.predict(arr)

            cursor.execute(f"UPDATE predict SET Pregnancies = {kehamilan}, Glucose = {glucose}, BloodPressure = {bloodpressure}, SkinThickness = {ketebalankulit}, Insulin = {insulin}, BMI = {BMI}, DiabetesPedigreeFunction = {DPF}, prediksi = {hasil_prediksi[0]} WHERE predict_id = {predict_id};")
            conn.commit()
            edit_predicted_status = True

        query = f"SELECT predict.user_id, users.nama, predict.age, predict.Pregnancies, predict.Glucose, predict.BloodPressure, predict.SkinThickness, predict.Insulin, predict.BMI, predict.DiabetesPedigreeFunction FROM predict INNER JOIN users ON predict.user_id = users.user_id WHERE predict_id = {predict_id};"
        cursor.execute(query)
        predicted = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_predict.html', predicted=predicted, edit_predicted_status=edit_predicted_status)

@app.route('/users')
def users():
    if 'admin_id' not in session:
        return redirect('/login_admin')
    else:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, username, nama, alamat, tanggal_lahir FROM users")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('users.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
def delete_user(user_id):
    if 'admin_id' not in session:
        return redirect('/login_admin')
    else:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Data berhasil dihapus!')
        return redirect('/users')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'admin_id' not in session:
        return redirect('/login_admin')
    else:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        edit_user_status = ""
        if request.method == 'POST':
            nama = request.form['nama']
            alamat = request.form['alamat']
            tanggal_lahir = request.form['tanggal_lahir']

            cursor.execute(f"UPDATE users SET nama = '{nama}', alamat = '{alamat}', tanggal_lahir = '{tanggal_lahir}' WHERE user_id = {user_id};")
            conn.commit()
            edit_user_status = True

        query = f"SELECT username, nama, alamat, tanggal_lahir FROM users WHERE user_id = {user_id};"
        cursor.execute(query)
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_user.html', user=user, edit_user_status=edit_user_status)

@app.route('/logout_admin')
def logout_admin():
    session.clear()
    return redirect('/login_admin')



if __name__ == '__main__':
    app.run(debug=True)