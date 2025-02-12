import json
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from pytrends.request import TrendReq
from google.auth.transport.requests import Request  # Add this import
import google.generativeai as genai
import requests

# Configure Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Function to get trending searches
def get_trending_searches():
    pytrend = TrendReq()
    df = pytrend.trending_searches(pn='indonesia')
    trending_searches = [{"rank": idx + 1, "term": row[0]} for idx, row in df.iterrows()]
    return trending_searches

def authenticate_youtube_api():
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    client_secrets_file = "YOUR_CLIENT_SECRET_FILE.json"
    token_file = "youtube_token.json"

    credentials = None

    # Check if token file exists
    if os.path.exists(token_file):
        # Load the saved credentials
        credentials = Credentials.from_authorized_user_file(token_file, scopes)

    # If no valid credentials are found, perform the OAuth flow
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, scopes
            )
            credentials = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(credentials.to_json())

    # Create the YouTube API client
    youtube = googleapiclient.discovery.build(
        "youtube", "v3", credentials=credentials
    )

    return youtube
# Function to fetch YouTube data
def fetch_youtube_data(queries):
    youtube = authenticate_youtube_api()  # Use the authenticated client

    filtered_results = []
    for query in queries:
        request = youtube.search().list(
            part="snippet",
            maxResults=15,
            q=query,
            regionCode="ID"
        )
        response = request.execute()
        
        # Filter the response for 'title' and 'description'
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            filtered_results.append({
                "title": snippet.get("title", ""),
                "description": snippet.get("description", "")
            })
    return filtered_results

# Main function
def main():
    # Refresh the file by opening it in write mode first
    with open("combined_data.txt", "w", encoding="utf-8") as file:
        file.write("")  # Clears the file content

    # Fetch trending searches
    print("Fetching trending searches...")
    trending_searches = get_trending_searches()
    print("Trending searches fetched successfully!")

    # Save trending searches to JSON and append to .txt file
    with open("combined_data.txt", "a", encoding="utf-8") as file:
        file.write("Google Trends:\n")
        file.write(json.dumps(trending_searches, ensure_ascii=False, indent=4))
        file.write("\n\n")

    # Fetch YouTube data
    print("Fetching YouTube data...")
    queries = ["nba", "football", "apple"]
    youtube_data = fetch_youtube_data(queries)
    print("YouTube data fetched successfully!")

    # Save YouTube data to JSON and append to .txt file
    with open("combined_data.txt", "a", encoding="utf-8") as file:
        file.write("YouTube Data:\n")
        file.write(json.dumps(youtube_data, ensure_ascii=False, indent=4))
        file.write("\n\n")

    # Read and append the mock Twitter data
    print("Appending mock Twitter data...")
    with open("twitter.json", "r", encoding="utf-8") as twitter_file:
        twitter_data = json.load(twitter_file)

    with open("combined_data.txt", "a", encoding="utf-8") as file:
        file.write("Mock Twitter Data:\n")
        file.write(json.dumps(twitter_data, ensure_ascii=False, indent=4))
        file.write("\n\n")

    # Read and append the content of prompt.txt
    print("Appending content from prompt.txt...")
    if os.path.exists("prompt.txt"):
        with open("prompt.txt", "r", encoding="utf-8") as prompt_file:
            prompt_content = prompt_file.read()

        with open("combined_data.txt", "a", encoding="utf-8") as file:
            file.write("Prompt Text:\n")
            file.write(prompt_content)
            file.write("\n\n")

    print("All data saved to 'combined_data.txt'")

    # Parse the combined data file and send it as a prompt to Gemini API
    print("Sending combined data to Gemini API...")
    with open("combined_data.txt", "r", encoding="utf-8") as file:
        combined_content = file.read().strip()

    # Create the model configuration
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
    )

    # Start a chat session
    chat_session = model.start_chat(
        history=[
            # You can provide the initial message or leave it empty
        ]
    )

    # Send the content of the file as a message to the model
    response = chat_session.send_message(combined_content)
    try:
        # Assuming the response from Gemini is in JSON format
        final_output = response.text
        print("Saving response to final_output.txt...")

    # Write the response to final_output.txt
        with open("final_output.txt", "w", encoding="utf-8") as txt_file:
            txt_file.write(final_output)
        print("Response saved to 'final_output.json'")
        with open("final_output.txt", "r") as file:
            lines = file.readlines()

    # Remove backticks and 'json'
        clean_data = "".join(line for line in lines if not line.strip().startswith("`") and line.strip() != "json")

    # Parse the clean data into a Python object
        fin_data = json.loads(clean_data)

    # Write to a .json file
        with open("output.json", "w") as file:
            json.dump(fin_data, file, indent=4)
    except json.JSONDecodeError:
            print("Error: Response is not in valid JSON format.")

    # URL
    url = "http://localhost:8085/mitra-cart/api/productRecommendations/insert"

    # Headers
    headers = {
    "accept": "application/json",
    "storeId": "10001",
    "channelId": "mitra-web",
    "requestId": "requestId",
    "clientId": "mitra",
    "username": "mitra",
    "businessChannel": "DESKTOP_WEB",
    "Content-Type": "application/json"
    }
    db_store_file_path = "output.json"
    try:
        with open(db_store_file_path, 'r') as file:
            payload = json.load(file)  # Load the JSON content into a Python object
    
        # Send POST request
        response = requests.post(url, headers=headers, json=payload)
    
        # Print response details
        if response.status_code == 200 or response.status_code == 201:
            print("Success:", response.json())
        else:
            print("Failed:", response.status_code, response.text)
    except FileNotFoundError:
        print(f"Error: File '{db_store_file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{db_store_file_path}'.")
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
