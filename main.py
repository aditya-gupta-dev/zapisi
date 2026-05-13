import polars

filename = "updated_records.csv"

df = polars.read_csv(filename)
