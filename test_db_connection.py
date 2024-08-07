import mysql.connector
from mysql.connector import Error

mysql_config = {
    'host': '198.100.45.83',
    'user': 'nilesh',
    'password': '!GuruDeva~13',
    'database': 'ashram',
    'port': 3306
}

def test_connection():
    try:
        connection = mysql.connector.connect(**mysql_config)
        if connection.is_connected():
            print('Successfully connected to the database')
            connection.close()
        else:
            print('Failed to connect to the database')
    except Error as e:
        print(f"Error: '{e}'")

if __name__ == '__main__':
    test_connection()
