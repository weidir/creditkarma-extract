# Import required libraries
import json
from datetime import datetime
import requests
from dotenv import dotenv_values
import pandas as pd

# Set the base URL for the CreditKarma GraphQL API
base_url = 'https://api.creditkarma.com/graphql'


def post_request(query: str, token: str, after_cursor=None) -> requests.Response:
    """
    Function to get list of transactions from CreditKarma GraphQL API
    Parameters:
        query (str): The GraphQL query to get the data
        token (str): The bearer access token to authenticate the request
        after_cursor (str): The cursor to get the next page of transactions
    Returns:
        requests.Response: The response from the API
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

    # Add the variables to the query
    query['variables'] = variables

    # Set the headers for the request
    headers = {
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json',
    }

    # Make a POST request to the CreditKarma GraphQL API
    response = requests.post('https://api.creditkarma.com/graphql', json=query, headers=headers)

    # Check if the request was successful
    if response.status_code != 200:
        if response.status_code == 401:
            
            if token and len(token) > 10:
                short_token = f"{token[:6]}...{token[-5:]}"
            print(f"401 error response, either token ({short_token}) was invalid or needs refresh")
        
        raise Exception(f"Response code: {response.status_code} Response body: {response.text}")
    
    return response


def extract_transactions() -> pd.DataFrame:
    """
    Function to extract all transactions for an account from CreditKarma GraphQL API
    """

    # Load environment variables from .env file
    env_vars = dotenv_values('.env')
    token = env_vars['token']

    # Load the JSON query to extract transactions
    with open('transactions_query.json', 'r') as f:
        query = json.load(f)

    # Perform the first request to get the first page of transactions
    response = post_request(query=query, token=token)
    response_json = response.json()

    # Load the transactions data from the response into a DataFrame
    trans_df = pd.json_normalize(response_json['data']['prime']['transactionsHub']['transactionPage']['transactions'])

    # Determine if there are more pages of transactions
    has_next_page = response_json['data']['prime']['transactionsHub']['transactionPage']['pageInfo']['hasNextPage']
    if not has_next_page:
        print("No more pages of transactions")
        return trans_df

    # Get the cursor for the next page of transactions
    end_cursor = response_json['data']['prime']['transactionsHub']['transactionPage']['pageInfo']['endCursor']

    # Loop through the pages of transactions until there are no more pages
    ix = 0
    while has_next_page:

        # Perform the next request to get the next page of transactions
        response_next = post_request(query=query, token=token, after_cursor=end_cursor)
        response_next_json = response_next.json()

        # Load the transactions data from the response into a DataFrame
        trans_df_next = pd.json_normalize(response_next_json['data']['prime']['transactionsHub']['transactionPage']['transactions'])

        # Append the most recent page of transactions to the DataFrame
        trans_df = pd.concat([trans_df, trans_df_next], axis=0, ignore_index=True)

        # Extract the cursor and next page flag for the next page of transactions
        page_info = response_next_json['data']['prime']['transactionsHub']['transactionPage']['pageInfo']
        end_cursor = page_info['endCursor']
        has_next_page = page_info['hasNextPage']

        # Print the number of transactions extracted
        print(f"Transactions page {ix+1} extracted - Has next page: {has_next_page}")
        ix += 1

    return trans_df


def main() -> None:
    """
    Main function to extract transactions from CreditKarma GraphQL API
    """

    # Capture the start time of the script
    start_tmstp = datetime.now()

    # Extract the transactions from the CreditKarma API
    trans_df = extract_transactions()
    print(f"Transactions extracted: {trans_df.shape[0]:,}")

    # Save the transactions to a CSV file
    trans_df.to_csv('transactions.csv', index=False)

    # Log the time taken to extract the transactions
    duration = datetime.now() - start_tmstp
    duration_str = f"{duration.seconds // 60} minutes, {duration.seconds % 60} seconds" if duration.seconds > 60 else f"{duration.seconds} seconds"
    print(f"Transaction data extraction duration: {duration_str}")


if __name__ == "__main__":
    main()