from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc

# สร้าง app และเชื่อมต่อฐานข้อมูลแค่ครั้งเดียว
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # เปลี่ยนเป็นคีย์จริง

conn_str = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=LAPTOP-SAF98KG5\\SQLEXPRESS;'
    'DATABASE=sellbook;'
    'UID=sa;'
    'PWD=M18042903;'
)

# ...existing code...

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if not session.get('user_id') or session.get('role') != 'seller':
        return redirect(url_for('login'))
    error = None
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        description = request.form['description']
        image_url = request.form['image_url']
        price = request.form['price']
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO books (title, author, description, image_url, price, sellerid) VALUES (?, ?, ?, ?, ?, ?)",
            (title, author, description, image_url, price, session['user_id'])
        )
        db.commit()
        db.close()
        return redirect(url_for('index'))
    return render_template('add_book.html', error=error)

# ...existing code...

@app.route('/delete_book/<int:book_id>', methods=['POST'], endpoint='delete_book')
def delete_book(book_id):
    if not session.get('user_id') or session.get('role') != 'seller':
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM books WHERE id=? AND sellerid=?", (book_id, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('index'))

# ...existing code...

@app.route('/confirm_order/<int:order_id>', methods=['POST'])
def confirm_order(order_id):
    if not session.get('user_id') or session.get('role') != 'customer':
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE orders SET status=? WHERE id=? AND user_id=?', ('จัดส่งสำเร็จ', order_id, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('my_orders'))

# ...existing code...

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    error = None
    current_username = None
    cursor.execute('SELECT username FROM users WHERE id=?', (session['user_id'],))
    row = cursor.fetchone()
    if row:
        current_username = row.username
    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        # ตรวจสอบว่าชื่อผู้ใช้ซ้ำหรือไม่
        cursor.execute('SELECT id FROM users WHERE username=? AND id<>?', (new_username, session['user_id']))
        if cursor.fetchone():
            error = 'ชื่อผู้ใช้นี้ถูกใช้แล้ว กรุณาเลือกชื่อใหม่'
        else:
            cursor.execute('UPDATE users SET username=?, password=? WHERE id=?', (new_username, new_password, session['user_id']))
            db.commit()
            session['username'] = new_username
            return redirect(url_for('index'))
    db.close()
    return render_template('edit_profile.html', error=error, current_username=current_username)




def get_db():
    return pyodbc.connect(conn_str)

@app.route('/seller_orders', methods=['GET', 'POST'])
def seller_orders():
    if not session.get('user_id') or session.get('role') != 'seller':
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        order_id = request.form['order_id']
        status = request.form['status']
        tracking = request.form.get('tracking', '')
        cursor.execute(
            "UPDATE orders SET status=?, tracking=? WHERE id=?",
            (status, tracking, order_id)
        )
        db.commit()
    # ดึงข้อมูลล่าสุดหลังอัปเดต เฉพาะที่ยังไม่สำเร็จ
    cursor.execute(
        '''
        SELECT o.id, o.address, o.status, o.tracking, u.username AS buyer_name, b.title
        FROM orders o
        JOIN books b ON o.book_id = b.id
        JOIN users u ON o.user_id = u.id
        WHERE b.sellerid = ? AND o.status != 'จัดส่งสำเร็จ'
        ORDER BY o.id DESC
        ''', (session['user_id'],)
    )
    orders = []
    for row in cursor.fetchall():
        orders.append({
            'id': row.id,
            'title': row.title,
            'buyer_name': row.buyer_name,
            'address': row.address,
            'status': row.status,
            'tracking': row.tracking if hasattr(row, 'tracking') else ''
        })

    db.close()
    return render_template('seller_orders.html', orders=orders)

def get_db():
    return pyodbc.connect(conn_str)

@app.route('/')
def index():
    books = []
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT b.id, b.title, b.author, b.description, b.image_url, b.sellerid, u.username AS seller_name
        FROM books b
        JOIN users u ON b.sellerid = u.id
        """
    )
    for row in cursor.fetchall():
        books.append({
            'id': row.id,
            'title': row.title,
            'author': row.author,
            'description': row.description,
            'image_url': row.image_url,
            'seller_name': row.seller_name,
            'sellerid': row.sellerid if hasattr(row, 'sellerid') else None
        })
    db.close()
    return render_template('index.html', books=books)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        # ตรวจสอบชื่อผู้ใช้ซ้ำ
        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            error = 'มีชื่อผู้ใช้นี้อยู่แล้ว กรุณาเลือกชื่อใหม่'
            db.close()
            return render_template('register.html', error=error)
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password, role)
        )
        db.commit()
        db.close()
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, role FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cursor.fetchone()
        db.close()
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'
    return render_template('login.html', error=error)
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    books = []
    db = get_db()
    cursor = db.cursor()
    user_id = session.get('user_id')
    role = session.get('role')
    if role == 'seller' and user_id:
        # ให้ seller เห็นเฉพาะหนังสือที่ตัวเองขาย
        if query:
            cursor.execute(
                """
                SELECT b.id, b.title, b.author, b.description, b.image_url, b.sellerid, u.username AS seller_name
                FROM books b
                JOIN users u ON b.sellerid = u.id
                WHERE b.sellerid = ? AND (b.title LIKE ? OR b.author LIKE ?)
                """,
                (user_id, '%' + query + '%', '%' + query + '%')
            )
        else:
            cursor.execute(
                """
                SELECT b.id, b.title, b.author, b.description, b.image_url, b.sellerid, u.username AS seller_name
                FROM books b
                JOIN users u ON b.sellerid = u.id
                WHERE b.sellerid = ?
                """,
                (user_id,)
            )
    else:
        if query:
            cursor.execute(
                """
                SELECT b.id, b.title, b.author, b.description, b.image_url, b.sellerid, u.username AS seller_name
                FROM books b
                JOIN users u ON b.sellerid = u.id
                WHERE b.title LIKE ? OR b.author LIKE ?
                """,
                ('%' + query + '%', '%' + query + '%')
            )
        else:
            cursor.execute(
                """
                SELECT b.id, b.title, b.author, b.description, b.image_url, b.sellerid, u.username AS seller_name
                FROM books b
                JOIN users u ON b.sellerid = u.id
                """
            )
    for row in cursor.fetchall():
        books.append({
            'id': row.id,
            'title': row.title,
            'author': row.author,
            'description': row.description,
            'image_url': row.image_url,
            'seller_name': row.seller_name,
            'sellerid': row.sellerid if hasattr(row, 'sellerid') else None
        })
    db.close()
    return render_template('search.html', books=books, query=query)
@app.route('/order/<int:book_id>', methods=['GET', 'POST'])
def order(book_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, title FROM books WHERE id=?", (book_id,))
    book = cursor.fetchone()
    db.close()
    if request.method == 'POST':
        address = request.form['address']
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO orders (user_id, book_id, address) VALUES (?, ?, ?)",
            (session['user_id'], book_id, address)
        )
        db.commit()
        db.close()
        return redirect(url_for('index'))
    return render_template('order.html', book=book)



@app.route('/sales_history')
def sales_history():
    if not session.get('user_id') or session.get('role') != 'seller':
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        '''
        SELECT o.id, o.address, o.status, o.tracking, u.username AS buyer_name, b.title
        FROM orders o
        JOIN books b ON o.book_id = b.id
        JOIN users u ON o.user_id = u.id
        WHERE b.sellerid = ? AND o.status = 'จัดส่งสำเร็จ'
        ORDER BY o.id DESC
        ''', (session['user_id'],)
    )
    orders = []
    for row in cursor.fetchall():
        orders.append({
            'id': row.id,
            'title': row.title,
            'buyer_name': row.buyer_name,
            'address': row.address,
            'status': row.status,
            'tracking': row.tracking if hasattr(row, 'tracking') else ''
        })
    db.close()
    return render_template('sales_history.html', orders=orders)
@app.route('/my_orders')
def my_orders():
    if not session.get('user_id') or session.get('role') != 'customer':
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        '''
        SELECT o.id, o.address, o.status, o.tracking, b.title, u.username AS seller_name
        FROM orders o
        JOIN books b ON o.book_id = b.id
        JOIN users u ON b.sellerid = u.id
        WHERE o.user_id = ? AND o.status != 'จัดส่งสำเร็จ'
        ORDER BY o.id DESC
        ''', (session['user_id'],)
    )
    orders = []
    for row in cursor.fetchall():
        orders.append({
            'id': row.id,
            'title': row.title,
            'seller_name': row.seller_name,
            'address': row.address,
            'status': row.status,
            'tracking': row.tracking if hasattr(row, 'tracking') else ''
        })
    db.close()
    return render_template('my_orders.html', orders=orders)

@app.route('/order_history')
def order_history():
    if not session.get('user_id') or session.get('role') != 'customer':
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        '''
        SELECT o.id, o.address, o.status, o.tracking, b.title, u.username AS seller_name
        FROM orders o
        JOIN books b ON o.book_id = b.id
        JOIN users u ON b.sellerid = u.id
        WHERE o.user_id = ? AND o.status = 'จัดส่งสำเร็จ'
        ORDER BY o.id DESC
        ''', (session['user_id'],)
    )
    orders = []
    for row in cursor.fetchall():
        orders.append({
            'id': row.id,
            'title': row.title,
            'seller_name': row.seller_name,
            'address': row.address,
            'status': row.status,
            'tracking': row.tracking if hasattr(row, 'tracking') else ''
        })
    db.close()
    return render_template('order_history.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)
