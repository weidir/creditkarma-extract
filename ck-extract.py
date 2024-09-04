# Import required libraries
import json
import os
import requests
import pandas as pd

# Set the base URL for the CreditKarma GraphQL API
base_url = 'https://api.creditkarma.com/graphql'


def get_transactions(after_cursor=None) -> pd.DataFrame:
    """
    Function to get list of transactions from CreditKarma GraphQL API
    Parameters:
        after_cursor (str): The cursor to get the next page of transactions
    Returns:
        pd.DataFrame: A DataFrame containing the transactions data in tabular form
    """

    # Define variables for the GraphQL query
    variables = {
        "input": {
            "paginationInput": {
                "afterCursor": after_cursor
            },
            "categoryInput": {
                "categoryId": None,
                "primeCategoryType": None
            },
            "datePeriodInput": {
                "datePeriod": None
            },
            "accountInput": {}
        }
    }

    # Define the GraphQL query
    params = {
        "query": "Your GraphQL query here",
        'variables': variables,
    }

    # Set the headers for the request
    headers = {
        'Authorization': f"Bearer {os.getenv('MY_ACCESS_TOKEN')}",
        'Content-Type': 'application/json',
    }

    # Make a POST request to the CreditKarma GraphQL API
    response = requests.post('https://api.creditkarma.com/graphql', json=params, headers=headers)

    # Check if the request was successful
    if response.status_code != 200:
        if response.status_code == 401:
            print(os.getenv('HELP_MESSAGE'))
            obfuscated = os.getenv('MY_ACCESS_TOKEN')
            if obfuscated and len(obfuscated) > 10:
                obfuscated = f"{obfuscated[:6]}...{obfuscated[-5:]}"
            print(f"401, either MY_ACCESS_TOKEN ({obfuscated}) was invalid or needs refresh")
            print("MY_ACCESS_TOKEN: should look like eyJra...kA2Uh  It'll be pretty long, the ... is just to shorten it for this message")
        
        raise Exception(f"error: {response.status_code} body: {response.text}")
    
    # Parse the response JSON
    response_json = response.json()
    print(f"CreditKarma GraphQL response: {response_json}")
    return response_json


def main() -> pd.DataFrame:
    """
    Main function of this script to recursively get all transactions from CreditKarma GraphQL API
    """

    # Initialize variables for data extraction and pagination
    total_transactions = []
    has_next_page = True
    cursor = os.getenv('START_CURSOR')

    with open("creditkarma_transactions.csv", "a") as out_file_csv, open("creditkarma_transactions.json", "a") as out_file_full_json:
        if os.stat("creditkarma_transactions.csv").st_size == 0:
            out_file_csv.write('"Date","Description","Original Description","Amount","Transaction Type","Category","Account Name","Labels","Notes"\n')

        while has_next_page:
            if cursor:
                print(f"getting next page cursor: {cursor}")
            resp = get_transactions(cursor)
            resp_data = resp.get('data', {}).get('prime', {}).get('transactionsHub', {}).get('transactionPage', {}).get('transactions')

            if not resp_data:
                print(f"expected data not in response: \n\n{resp}")
                print("If your response looks like \n\n")
                print('{"data":{"prime":{"transactionsHub":{}}}}')
                print("then you probably need to re-authenticate on the website by visiting https://www.creditkarma.com/networth/transaction to get a mobile code.")

            tra_batch = []
            for tra in resp_data:
                out_file_full_json.write(json.dumps(tra) + "\n")

                desc = tra['description']
                date = tra['date']
                status = tra['status']

                tra_type = 'debit' if tra['amount']['value'] < 0 else 'credit'
                amt = abs(tra['amount']['value'])

                acct = tra.get('account', {}).get('name')
                if not acct:
                    print(f"not sure why, but missing account name from the transaction: \n\n{tra}\n\n")
                cat = tra.get('category', {}).get('name')
                if not cat:
                    print(f"not sure why, but missing category name from the transaction: \n\n{tra}\n\n")
                merch = tra.get('merchant', {}).get('name')
                if not merch:
                    print(f"not sure why, but missing merchant name from the transaction: \n\n{tra}\n\n")

                out_file_csv.write(f'"{date}","{merch}","{desc}","{amt}","{tra_type}","{cat}","{acct}","",""\n')

                new_tra = {
                    'desc': desc,
                    'date': date,
                    'status': status,
                    'amt': amt,
                    'tra_type': tra_type,
                    'acct': acct,
                    'cat': cat,
                    'merch': merch
                }
                print(new_tra)  # Equivalent to `debug` in Ruby
                tra_batch.append(new_tra)

            total_transactions += tra_batch
            print(f"total transactions: {len(total_transactions)}, last date: {tra_batch[-1]['date']}")

            page_info = resp['data']['prime']['transactionsHub']['transactionPage']['pageInfo']
            cursor = page_info['endCursor']
            has_next_page = page_info['hasNextPage']

    print("done")



if __name__ == "__main__":
    main()