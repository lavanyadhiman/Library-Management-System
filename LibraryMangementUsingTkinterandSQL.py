import tkinter as tk
from datetime import datetime
import mysql.connector
import random
from tkinter import PhotoImage, messagebox

con = mysql.connector.connect(host="localhost", user="root", password="root12", database="library_management")
cur = con.cursor()

def shownew():
    sw = tk.Tk()
    sw.geometry("600x250")
    sw.title("Welcome")

    # Search Frame
    search_frame = tk.Frame(sw)
    search_frame.pack(pady=10)

    tk.Label(search_frame, text="Search:").grid(row=0, column=0, padx=5)
    search_entry = tk.Entry(search_frame)
    search_entry.grid(row=0, column=1, padx=5)
    tk.Button(search_frame, text="Search", command=lambda: search_books(search_entry.get())).grid(row=0, column=2, padx=5)

    # Button Frame
    button_frame = tk.Frame(sw)
    button_frame.pack(pady=10)

    tk.Button(button_frame, text="Return Book", command=return_book).grid(row=0, column=0, padx=10)
    tk.Button(button_frame, text="View Issued Books", command=view_user_issued_books).grid(row=0, column=1, padx=10)
    tk.Button(button_frame, text="View Billing Records", command=view_user_billing).grid(row=0, column=2, padx=10)
    tk.Button(button_frame, text="Pay Bill", command=open_payment_window).grid(row=0, column=3, padx=10)
    tk.Button(button_frame, text="Logout", command=sw.destroy).grid(row=1, column=1, columnspan=2, pady=10)

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
    try:
        if not check_availability(book_id):
            messagebox.showwarning("Error", f"Book {book_id} is not available.")
            return

        price_query = "SELECT price FROM books WHERE book_id = %s"
        cur.execute(price_query, (book_id,))
        price = cur.fetchone()[0]

        con.start_transaction()

        query = "INSERT INTO loans (book_id, user_id, loan_date) VALUES (%s, %s, %s)"
        cur.execute(query, (book_id, user_id, datetime.now().date()))
        update_query = "UPDATE books SET available = FALSE WHERE book_id = %s"
        cur.execute(update_query, (book_id,))

        billing_query = "INSERT INTO billing (user_id, book_id, issue_date, price) VALUES (%s, %s, %s, %s)"
        cur.execute(billing_query, (user_id, book_id, datetime.now().date(), price))

        con.commit()
        messagebox.showinfo("Success", f"Book {book_id} issued successfully.")
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Error: {err}")
        con.rollback()
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        con.rollback()

def return_book():
    user_id = int(user_id_entry.get())
    book_id = int(book_id_entry.get())
    con.start_transaction()

    query = "UPDATE loans SET return_date = %s WHERE book_id = %s AND user_id = %s AND return_date IS NULL"
    cur.execute(query, (datetime.now().date(), book_id, user_id))

    if cur.rowcount == 0:
        messagebox.showwarning("Error", "No outstanding loan found for this book.")
        con.rollback()
        return

    update_query = "UPDATE books SET available = TRUE WHERE book_id = %s"
    cur.execute(update_query, (book_id,))

    billing_query = "UPDATE billing SET return_date = %s WHERE book_id = %s AND user_id = %s AND return_date IS NULL"
    cur.execute(billing_query, (datetime.now().date(), book_id, user_id))

    con.commit()
    messagebox.showinfo("Success", "Book returned successfully.")

def view_user_issued_books():
    user_id = int(user_id_entry.get())
    query = """
    SELECT b.title, b.author, l.book_id, l.loan_date, l.return_date 
    FROM loans l
    JOIN books b ON l.book_id = b.book_id
    WHERE l.user_id = %s AND l.return_date IS NULL
    """
    cur.execute(query, (user_id,))
    loans = cur.fetchall()
    if not loans:
        messagebox.showinfo("Issued Books", "No books issued.")
    else:
        loans_list = "\n".join([str(loan) for loan in loans])
        messagebox.showinfo("Issued Books", loans_list)

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

def pay_bill():
    user_id = int(user_id_entry.get())
    query = """
    SELECT SUM(b.amount_due) 
    FROM billing b
    JOIN loans l ON b.loan_id = l.loan_id
    WHERE l.user_id = %s
    """
    cur.execute(query, (user_id,))
    result = cur.fetchone()
    total_amount_due = result[0] if result[0] is not None else 0

    if total_amount_due == 0:
        messagebox.showinfo("Payment", "No outstanding bills.")
        return

    amt = float(amount_entry.get())

    if amt < total_amount_due:
        messagebox.showwarning("Error", "Amount entered is less than the total amount due. Please pay the full amount.")
        return

    update_query = """
    UPDATE billing
    JOIN loans ON billing.loan_id = loans.loan_id
    SET billing.amount_due = 0
    WHERE loans.user_id = %s AND billing.amount_due > 0
    """
    cur.execute(update_query, (user_id,))

    con.commit()
    t_id = [random.randint(1, 9) for _ in range(5)]
    t_id_str = ''.join(map(str, t_id))
    messagebox.showinfo("Success", f"Bill paid successfully.\nTransaction id: {t_id_str}")

def checkvalidity():
    global user_id
    user_id = int(user_id_entry.get())
    email = email_entry.get()

    cur.execute("SELECT * FROM users WHERE user_id = %s AND email = %s", (user_id, email))
    if cur.fetchone():
        messagebox.showinfo("Login Success", "Login Successful")
        shownew()
    else:
        messagebox.showerror("Error", "Invalid User ID or Email")

# Login Window
root = tk.Tk()
root.geometry("300x200")
root.title("Login")

# Login Frame
login_frame = tk.Frame(root)
login_frame.pack(pady=20)

tk.Label(login_frame, text="User ID:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
user_id_entry = tk.Entry(login_frame)
user_id_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(login_frame, text="Email:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
email_entry = tk.Entry(login_frame)
email_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Button(root, text="Login", command=checkvalidity).pack(pady=20)

root.mainloop()
