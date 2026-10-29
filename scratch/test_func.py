import os
import datetime as dt
import csv
from fastapi.responses import FileResponse

HERE = os.path.dirname(os.path.abspath(__file__))
test_file = os.path.join(HERE, "test.csv")
with open(test_file, "w") as f:
    f.write("a,b\n1,2\n")

def export_trades_csv():
    filename = f"closed_trades_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return FileResponse(test_file, media_type="text/csv", filename=filename)

res = export_trades_csv()
print("Success:", res.media_type, res.filename)

