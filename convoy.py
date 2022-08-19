# Write your code here
import pandas as pd
import re
import sqlite3
import json
from lxml import etree


def excel_to_csv(file, sheet_name):
    """Converts an Excel file to a CSV file"""
    df = pd.read_excel(file + ".xlsx", sheet_name=sheet_name, dtype=str)
    df.to_csv(f'{file}.csv', index=None, header=True)
    if df.shape[0] == 1:
        print(f'{df.shape[0]} line was added to {file}.csv')
    else:
        print(f'{df.shape[0]} lines were added to {file}.csv')
    return f"{file}.csv"


def check_csv(file):
    """Creates new CSV file with formatted cells from provided CSV file."""
    df = pd.read_csv(file + ".csv")
    counter = 0
    df_out = df.replace(to_replace = '\D', value = '', regex = True)
    for column in df:
        for row in range(df.shape[0]):
            if df[column].values[row] != df_out[column].values[row]:
                counter = counter + 1 #i know it's ugly, but it works
    df_out = df_out.astype(int)
    df_out.to_csv(f'{file}[CHECKED].csv', index=None, header=True)
    if counter > 1:
        print(f'{counter} cells were corrected in {file}[CHECKED].csv')
    else:
        print(f'{counter} cell was corrected in {file}.csv')



class Vehicle:
    def __init__(self, vehicle_id, engine_capacity, fuel_consumption, maximum_load):
        self.vehicle_id = vehicle_id
        self.engine_capacity = engine_capacity #it's actually fuel capacity
        self.fuel_consumption = fuel_consumption
        self.maximum_load = maximum_load
        self.score = 0
        fuel_used = 450/100 * fuel_consumption
        pit_stops = fuel_used // engine_capacity
        if pit_stops == 0:
            self.score += 2
        elif pit_stops == 1:
            self.score += 1
        if fuel_used <= 230:
            self.score += 2
        else:
            self.score += 1
        if maximum_load >= 20:
            self.score += 2

    def static_method(row):
        print("something")
        print(row)
        return row["vehicle_id"], row["engine_capacity"], row["fuel_consumption"], row["maximum_load"]


    def get_score(self):
        return self.score


def csv_to_sqlite(file):
    """Creates a SQLite3 database from a checked CSV file."""
    df = pd.read_csv(file + ".csv")
    output_name = re.sub('\[CHECKED]$', '', file)
    df_head = df.columns.values
    conn = sqlite3.connect(f'{output_name}.s3db')
    cursor_name = conn.cursor()
    cursor_name.execute('DROP TABLE IF EXISTS convoy')
    cursor_name.execute(f'''CREATE TABLE {"convoy"} (
    {df_head[0]} INT PRIMARY KEY,
    {df_head[1]} INT NOT NULL, 
    {df_head[2]} INT NOT NULL, 
    {df_head[3]} INT NOT NULL,
    {"score"} INT NOT NULL
    );''')
    cols = '"' + '","'.join([str(i) for i in df.columns.tolist()]) + '"'
    cols += ',"score"'
    # Insert DataFrame records one by one.
    for i, row in df.iterrows():
        sql = 'INSERT INTO convoy (' + cols + ') VALUES (' + '%s,'*(len(row)-1) + '%s,%s)'
        vehicle = Vehicle(row["vehicle_id"], row["engine_capacity"], row["fuel_consumption"], row["maximum_load"])
        data = tuple(row) + (vehicle.get_score(),)
        cursor_name.execute(sql % data)
    inserted_count = cursor_name.execute("select count(*) from convoy;").fetchall()[0][0]
    if inserted_count == 1:
        print(f"{inserted_count} record was inserted into {output_name}.s3db")
    else:
        print(f"{inserted_count} records were inserted into {output_name}.s3db")
    conn.commit()
    cursor_name.close()
    conn.close()
    return df

def print_sql(file):
    conn = sqlite3.connect(f'{file}.s3db')
    cursor_name = conn.cursor()
    cursor_name.execute(f''' 
    SELECT * FROM convoy
    ''')
    myresult = cursor_name.fetchall()
    for x in myresult:
        print(x)
    conn.commit()
    cursor_name.close()
    conn.close()


def df_to_xml(df):
    """Creates a XML from a df."""
    xml = ['<convoy>']
    for i, row in df.iterrows():
        xml.append('<vehicle>')
        for fld in row.index:
            xml.append(f'<{fld}>{row[fld]}</{fld}>')
        xml.append('</vehicle>')
    xml.append('</convoy>')
    return ''.join(xml)


def sql_to_json_and_xml(file):
    """Converts an SQLite3 database file to a JSON file and XML file"""
    conn = sqlite3.connect(f'{file}.s3db')
    sql_json = """SELECT * FROM   
    convoy WHERE score > 3"""
    sql_xml = """SELECT * FROM   
    convoy WHERE score < 4"""

    df_json = pd.read_sql_query(sql_json, conn)
    df_xml = pd.read_sql_query(sql_xml, conn)
    del df_json['score']
    del df_xml['score']
    exp = {"convoy": json.loads(df_json.to_json(orient='records'))}
    with open(f'{file}.json', 'w') as json_file:
        json.dump(exp, json_file, indent=4)
    saved = len(df_json)
    if saved == 1:
        print(f"{saved} vehicle was saved into {file}.json")
    else:
        print(f"{saved} vehicles were saved into {file}.json")
    conn.commit()
    conn.close()
    with open(f'{file}.xml', 'w') as xml_file:
        xml_file.write(df_to_xml(df_xml))
    saved = len(df_xml)
    if saved == 1:
        print(f"{saved} vehicle was saved into {file}.xml")
    else:
        print(f"{saved} vehicles were saved into {file}.xml")






if __name__ == '__main__':
    print("Input file name")
    file_name = input()
    file_name_arr = file_name.split(".")

    if file_name_arr[1] == 'xlsx':
        excel_to_csv(file_name_arr[0], 'Vehicles')
        file_name_arr[1] = "csv"
    if file_name_arr[1] == 'csv':
        if file_name_arr[0].endswith('[CHECKED]'):
            file_name_arr[0] = re.sub('\[CHECKED]$', '', file_name_arr[0])
        else:
            check_csv(file_name_arr[0])
        csv_to_sqlite(file_name_arr[0] + "[CHECKED]")
        file_name_arr[1] = "s3db"
    if file_name_arr[1] == 's3db':
        sql_to_json_and_xml(file_name_arr[0])


