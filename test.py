import os.path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 1) allow read + write
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 2) your sheet
SPREADSHEET_ID = "1J8Sd8gDlPq-sE0X_xKT3JJanCB8A3-aCuaDATlHi4tk"   # <- put UnionDentalDB id here
SHEET_NAME = "Page1"                             


def get_service():
    """Return an authenticated Sheets service."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=1796)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    service = build("sheets", "v4", credentials=creds)
    return service

def get_header(service):
    """Read header row."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1:I1",
    ).execute()
    return result.get("values", [])[0]

def get_rows(service):
    """Read all inventory rows (skip header)."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A2:I",
    ).execute()
    return result.get("values", [])


def update_row(service, item_id: str, new_qty: int):
    """Find row by Item ID and update stock + last updated."""
    # 1) read all
    rows = get_rows(service)
    target_row = None
    for i, row in enumerate(rows, start=2):  # start=2 because A2 is first data row
        if len(row) > 0 and row[0] == item_id:
            target_row = i
            break

    if not target_row:
        raise ValueError(f"Item ID {item_id} not found")

    # F column = Stock Qty (6th col)
    stock_range = f"{SHEET_NAME}!F{target_row}"
    updated_range = f"{SHEET_NAME}!I{target_row}"

    body_stock = {"values": [[new_qty]]}
    body_time = {"values": [[datetime.now().isoformat(timespec="seconds")]]}

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=stock_range,
        valueInputOption="USER_ENTERED",
        body=body_stock,
    ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=updated_range,
        valueInputOption="USER_ENTERED",
        body=body_time,
    ).execute()

    print(f"Updated {item_id} → {new_qty}")


def append_item(service, row_values):
    """Append a new item to Page1."""
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:I",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_values]},
    ).execute()


def main():
    try:
        service = get_service()

        # Example 1: read
        header = get_header(service)
        rows = get_rows(service)
        print(f"Header: {header}")
        print(f"Current rows:")
        for r in rows:
            print(r)

        # Example 2: update stock for D001
        # update_row(service, "10000002", 99)

        # Example 3: append a new item
        # append_item(service, [
        #     "D010", "QR-D010", "Suction Tips", "Bedford", "bag", 50, 10, "Patterson",
        #     datetime.now().isoformat(timespec="seconds")
        # ])

    except HttpError as err:
        print(err)


if __name__ == "__main__":
    main()
