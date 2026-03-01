
import duckdb
import pandas as pd
from datetime import datetime

parquet_path = '/Users/m1air/Desktop/MCS_ChatBot/data_cache/master_2026-Feb-27.parquet'
con = duckdb.connect()

def run_test(name, sql):
    print(f"\n=== Testing: {name} ===")
    try:
        # Create view 'df' like the bot does
        con.execute(f"CREATE OR REPLACE VIEW df AS SELECT * FROM read_parquet('{parquet_path}')")
        res = con.execute(sql).fetchdf()
        print(f"Results found: {len(res)}")
        if not res.empty:
            print(res.head(5).to_string())
        else:
            print("No results matching criteria.")
    except Exception as e:
        print(f"Error: {e}")

# 1. USA Shipments
run_test("USA Shipments", """
SELECT container_number, discharge_port, final_destination, shipment_status 
FROM df 
WHERE discharge_port ILIKE '%(US%)' OR final_destination ILIKE '%(US%)'
LIMIT 5
""")

# 2. Arrived in DP but Not Delivered to FD
run_test("Arrived DP / Not Delivered FD", """
SELECT container_number, discharge_port, ata_dp_date, delivery_to_consignee_date, shipment_status
FROM df 
WHERE ata_dp_date IS NOT NULL AND delivery_to_consignee_date IS NULL
LIMIT 5
""")

# 3. Plan Deviation (In-DC vs Delivered)
run_test("Plan Deviation (In-DC vs Delivered)", """
SELECT container_number, "in-dc_date", delivery_to_consignee_date
FROM df 
WHERE "in-dc_date" IS NOT NULL AND delivery_to_consignee_date IS NOT NULL 
      AND "in-dc_date" != delivery_to_consignee_date
LIMIT 5
""")
