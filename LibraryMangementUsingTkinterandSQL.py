import tkinter as tk
from datetime import datetime
import mysql.connector
import random
from tkinter import PhotoImage, messagebox

con = mysql.connector.connect(host="localhost", user="root", password="root12", database="library_management")
cur = con.cursor()
def shownew():
    sw = tk.Tk()
    sw.geometry("600x300") 
    sw.title("Welcome")
    
   
    tk.Label(sw, text="Search:").place(x=10, y=10)
    search_entry = tk.Entry(sw)
    search_entry.place(x=70, y=10, width=200)
    tk.Button(sw, text="Search", command=lambda: search_books(search_entry.get())).place(x=280, y=10)

  
    
    
    tk.Button(sw, text="View Issued Books", command=view_user_issued_books).place(x=140, y=50, width=120)
    tk.Button(sw, text="Logout", command=sw.destroy).place(x=210, y=70, width=120)

    sw.mainloop()




def open_payment_window():
    pw = tk.Tk()
    pw.geometry("300x200")
    pw.title("Pay Bill")

    tk.Label(pw, text="Amount to Pay:").grid(row=0, column=0, padx=20, pady=20)
    global amount_entry
    amount_entry = tk.Entry(pw)
    amount_entry.grid(row=0, column=1, padx=20, pady=20)

    tk.Button(pw, text="Pay", command=pay_bill).grid(row=1, column=0, columnspan=2, pady=20)
    pw.mainloop()

def search_books(search_term):
    query = """
    SELECT * FROM books 
    WHERE title LIKE %s 
    OR author LIKE %s 
    OR genre LIKE %s 
    OR published_year = %s
    """
    cur.execute(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", search_term))
    search_results = cur.fetchall()
    show_search_results(search_results)

def show_search_results(search_results):
    results_window = tk.Toplevel()
    results_window.title("Search Results")

    canvas = tk.Canvas(results_window)
    scrollbar = tk.Scrollbar(results_window, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    image = PhotoImage(file=r"C:\Users\Lavanya\OneDrive\Desktop\pycode\book.png")

    for book in search_results:
        book_frame = tk.Frame(scrollable_frame, padx=10, pady=10)
        book_frame.pack(fill="x", expand=True)

        image_label = tk.Label(book_frame, image=image)
        image_label.image = image
        image_label.pack(side="left")

        details_text = f"Title: {book[1]}\nAuthor: {book[2]}\nGenre: {book[4]}\nYear: {book[3]}"
        details_label = tk.Label(book_frame, text=details_text, anchor="w", justify="left")
        details_label.pack(side="left", fill="x", expand=True)

        issue_button = tk.Button(book_frame, text="Issue Book", command=lambda b=book[0]: issue_book(b))
        issue_button.pack(side="left", padx=10)

def check_availability(book_id):
    query = "SELECT available FROM books WHERE book_id = %s"
    cur.execute(query, (book_id,))
    result = cur.fetchone()
    return result and result[0]

def issue_book(book_id):
    global con, cur
    if not check_availability(book_id):
        messagebox.showwarning("Error", f"Book {book_id} is not available.")
        return

    query = "INSERT INTO requests (book_id, user_id, request_date, request_type) VALUES (%s, %s, %s, 'issue')"
    cur.execute(query, (book_id, user_id, datetime.now().date()))
    con.commit()
    messagebox.showinfo("Request Sent", "Book issue request sent.")



def issue_book_from_request(request_id):
    query = "SELECT book_id, user_id FROM requests WHERE request_id = %s"
    cur.execute(query, (request_id,))
    request = cur.fetchone()
    if not request:
        messagebox.showwarning("Error", "Request not found.")
        return

    book_id, user_id = request
    try:
        price_query = "SELECT price FROM books WHERE book_id = %s"
        cur.execute(price_query, (book_id,))
        price = cur.fetchone()[0]

        con.start_transaction()

        query = "INSERT INTO loans (book_id, user_id, loan_date) VALUES (%s, %s, %s)"
        cur.execute(query, (book_id, user_id, datetime.now().date()))
        update_query = "UPDATE books SET available = FALSE WHERE book_id = %s"
        cur.execute(update_query, (book_id,))

        billing_query = "INSERT INTO billing (loan_id, amount_due, billing_date) VALUES (LAST_INSERT_ID(), %s, %s)"
        cur.execute(billing_query, (price, datetime.now().date()))

        update_request_query = "UPDATE requests SET status = 'accepted' WHERE request_id = %s"
        cur.execute(update_request_query, (request_id,))

        con.commit()
        messagebox.showinfo("Success", "Book issued successfully.")
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Error: {err}")
        con.rollback()
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        con.rollback()


def return_book_from_request(request_id):
    query = "SELECT book_id, user_id FROM requests WHERE request_id = %s"
    cur.execute(query, (request_id,))
    request = cur.fetchone()
    if not request:
        messagebox.showwarning("Error", "Request not found.")
        return

    book_id, user_id = request
    try:
        con.start_transaction()

        query = "UPDATE loans SET return_date = %s WHERE book_id = %s AND user_id = %s AND return_date IS NULL"
        cur.execute(query, (datetime.now().date(), book_id, user_id))

        if cur.rowcount == 0:
            messagebox.showwarning("Error", "No outstanding loan found for this book.")
            con.rollback()
            return

        update_query = "UPDATE books SET available = TRUE WHERE book_id = %s"
        cur.execute(update_query, (book_id,))

        billing_query = "UPDATE billing SET return_date = %s WHERE loan_id = (SELECT loan_id FROM loans WHERE book_id = %s AND user_id = %s)"
        cur.execute(billing_query, (datetime.now().date(), book_id, user_id))

        update_request_query = "UPDATE requests SET status = 'accepted' WHERE request_id = %s"
        cur.execute(update_request_query, (request_id,))

        con.commit()
        messagebox.showinfo("Success", "Book returned successfully.")
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Error: {err}")
        con.rollback()
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        con.rollback()


def view_user_issued_books():
    user_id = int(user_id_entry.get())  # Get user ID from entry field
    query = """
    SELECT b.book_id, b.title, b.author, l.loan_date 
    FROM loans l
    JOIN books b ON l.book_id = b.book_id
    WHERE l.user_id = %s AND l.return_date IS NULL
    """
    cur.execute(query, (user_id,))
    loans = cur.fetchall()

    issued_window = tk.Toplevel()
    issued_window.title("Issued Books")
    issued_window.geometry("600x400")

    for i, (book_id, title, author, loan_date) in enumerate(loans):
        book_frame = tk.Frame(issued_window, padx=10, pady=5)
        book_frame.pack(fill="x", pady=2)

        tk.Label(book_frame, text=f"Title: {title}").pack(side="left")
        tk.Label(book_frame, text=f"Author: {author}").pack(side="left")
        tk.Label(book_frame, text=f"Loan Date: {loan_date}").pack(side="left")

        return_button = tk.Button(book_frame, text="Return Book", command=lambda b_id=book_id: return_book(b_id))
        return_button.pack(side="left", padx=5)

        pay_button = tk.Button(book_frame, text="Pay Bill", command=lambda b_id=book_id: pay_bill(b_id))
        pay_button.pack(side="left", padx=5)

def return_book(book_id):
    # Implement the return_book logic here
    query = "INSERT INTO requests (book_id, user_id, request_date, request_type) VALUES (%s, %s, %s, 'return')"
    cur.execute(query, (book_id, user_id, datetime.now().date()))
    con.commit()
    messagebox.showinfo("Request Sent", "Book return request sent.")

def pay_bill(book_id):
    # Implement the pay_bill logic here
    # For simplicity, assuming the function pays for the entire amount of the bill for a specific book
    query = """
    SELECT SUM(b.amount_due) 
    FROM billing b
    JOIN loans l ON b.loan_id = l.loan_id
    WHERE l.book_id = %s
    """
    cur.execute(query, (book_id,))
    result = cur.fetchone()
    total_amount_due = result[0] if result[0] is not None else 0

    if total_amount_due == 0:
        messagebox.showinfo("Payment", "No outstanding bills.")
        return

    amt = float(amount_entry.get())  # Assuming amount_entry is a global variable for the payment amount

    if amt < total_amount_due:
        messagebox.showwarning("Error", "Amount entered is less than the total amount due. Please pay the full amount.")
        return

    update_query = """
    UPDATE billing
    JOIN loans ON billing.loan_id = loans.loan_id
    SET billing.amount_due = 0
    WHERE loans.book_id = %s AND billing.amount_due > 0
    """
    cur.execute(update_query, (book_id,))

    con.commit()
    t_id = [random.randint(1, 9) for _ in range(5)]
    t_id_str = ''.join(map(str, t_id))
    messagebox.showinfo("Success", f"Bill paid successfully.\nTransaction id: {t_id_str}")


def view_user_billing():
    user_id = int(user_id_entry.get())
    query = """
    SELECT b.title, b.author, bi.amount_due, bi.billing_date
    FROM loans l
    JOIN books b ON l.book_id = b.book_id
    JOIN billing bi ON l.loan_id = bi.loan_id
    WHERE l.user_id = %s
    """
    cur.execute(query, (user_id,))
    results = cur.fetchall()
    if not results:
        messagebox.showinfo("Billing Records", "No billing records found.")
    else:
        billing_list = "\n".join([str(record) for record in results])
        messagebox.showinfo("Billing Records", billing_list)

def admin_request_management():
    global request_frame  # Declare request_frame as global if you use it outside of this function
    aw = tk.Tk()
    aw.geometry("600x400")
    aw.title("Request Management")

    # Initialize request_frame here
    request_frame = tk.Frame(aw)
    request_frame.pack(fill="x")

    def refresh_requests():
        for widget in request_frame.winfo_children():
            widget.destroy()
        
        query = "SELECT * FROM requests WHERE status = 'pending'"
        cur.execute(query)
        pending_requests = cur.fetchall()

        for request in pending_requests:
            req_frame = tk.Frame(request_frame)
            req_frame.pack(fill="x")
            
            tk.Label(req_frame, text=f"Request ID: {request[0]}").pack(side="left", padx=10)
            tk.Label(req_frame, text=f"Book ID: {request[1]}").pack(side="left", padx=10)
            tk.Label(req_frame, text=f"User ID: {request[2]}").pack(side="left", padx=10)
            tk.Label(req_frame, text=f"Type: {request[4]}").pack(side="left", padx=10)
            tk.Label(req_frame, text=f"Date: {request[3]}").pack(side="left", padx=10)
            tk.Button(req_frame, text="Accept", command=lambda r_id=request[0]: update_request(r_id, 'accepted')).pack(side="left", padx=10)
            tk.Button(req_frame, text="Reject", command=lambda r_id=request[0]: update_request(r_id, 'rejected')).pack(side="left", padx=10)

    def update_request(request_id, status):
        query = "UPDATE requests SET status = %s WHERE request_id = %s"
        cur.execute(query, (status, request_id))
        con.commit()
        refresh_requests()

    tk.Button(aw, text="Refresh", command=refresh_requests).pack(pady=10)
    refresh_requests()

def admin():
    aw = tk.Tk()
    aw.geometry("600x250")
    aw.title("Hello Admin!")
    tk.Button(aw, text="Validate Requests", command=admin_request_management).place(x=100, y=100)
    # Other admin functionalities...

def checkvalidity():
    global user_id
    user_id = int(user_id_entry.get())
    email = email_entry.get()

    cur.execute("SELECT * FROM users WHERE user_id = %s AND email = %s", (user_id, email))
    result = cur.fetchone()  
    if result:
        messagebox.showinfo("Login Success", "Login Successful")
        user_type = result[3] 
        if user_type == 'Admin':
            admin()
        else:
            shownew()
                        
    else:
        messagebox.showerror("Error", "Invalid User ID or Email")
root = tk.Tk()
root.geometry("300x200")
root.title("Login")

login_frame = tk.Frame(root)
login_frame.pack(pady=20)

tk.Label(login_frame, text="User ID:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
user_id_entry = tk.Entry(login_frame)
user_id_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(login_frame, text="Email:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
email_entry = tk.Entry(login_frame)
email_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Button(root, text="Login", command=checkvalidity).pack(pady=20)

