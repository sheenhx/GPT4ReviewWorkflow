import os
import requests
import json
import openai
import math

def get_review():
    ACCESS_TOKEN = os.getenv("GITHUB_TOKEN")
    GIT_COMMIT_HASH = os.getenv("GIT_COMMIT_HASH")
    model = "gpt-4"
    openai.api_key = os.getenv("OPENAI_API_KEY")
    openai.organization = os.getenv("OPENAI_ORG_KEY")
    pr_link = os.getenv("LINK")

    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "authorization": f"Bearer {ACCESS_TOKEN}",
    }
    
    OWNER = pr_link.split("/")[-4]
    REPO = pr_link.split("/")[-3]
    PR_NUMBER = pr_link.split("/")[-1]

    # Get the diff of the pull request
    pr_details_url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}"
    pr_details_response = requests.get(pr_details_url, headers=headers)
    if pr_details_response.status_code != 200:
        print(f"Error fetching pull request details: {pr_details_response.status_code} - {pr_details_response.text}")
        return
    
    complete_prompt = '''    
    Act as a code reviewer of a Pull Request, use markdown in response, check typo and try to understand and summarize the logic.
    Your response is limited to 4000 characters, try to be precise. Try to find as many problems as possible.
    The patch or patches for review are below:    
    '''
    prompt = complete_prompt + pr_details_response.text

    print(f"\nPrompt sent to GPT-4: {prompt}\n")

    AVG_CHAR_PER_TOKEN = 4
    CHUNK_SIZE = 5000
    num_chunks = math.ceil(len(prompt) / AVG_CHAR_PER_TOKEN / CHUNK_SIZE)
    reviews = []

    for i in range(num_chunks):
        chunk_start = i * CHUNK_SIZE * AVG_CHAR_PER_TOKEN
        chunk_end = (i+1) * CHUNK_SIZE * AVG_CHAR_PER_TOKEN
        chunk = prompt[chunk_start:chunk_end]
        messages = [
            {"role": "system", "content": "You are an experienced software developer."},
            {"role": "user", "content": chunk},
        ]

        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=1024, # here is the amount of the text in answers
                top_p=1,
                frequency_penalty=0.3,
                presence_penalty=0.6,
            )
        except openai.error.RateLimitError as e:
            print(f"RateLimitError: {e}")
            print("You have exceeded your current quota. Please check your plan and billing details.")
            return
        except openai.error.InvalidRequestError as e:
            print(f"InvalidRequestError: {e}")
            print("Your request is invalid. Please check the input and try again.")
            return
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return

        reviews.append(response["choices"][0]["message"]["content"])

    for review in reviews:
        data = {"body": review, "commit_id": GIT_COMMIT_HASH, "event": "COMMENT"}
        data = json.dumps(data)
        print(f"\nResponse from GPT-4: {data}\n")

        response = requests.post(
            f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/reviews",
            headers=headers,
            data=data,
        )
        print(response.json())

if __name__ == "__main__":
    get_review()
