import requests

url = "https://www.fast2sms.com/dev/bulkV2"

# ✅ Replace with your actual phone number
numbers = "9611402986"  

# ✅ Replace with your own message
message = "Hello Neha! This is a test SMS from Fast2SMS using Python."

# ✅ Replace with your Fast2SMS API key
api_key = "CELR3Zg21VMUIiWy4rzqnS6fYBaxNdsHlOhpJ7DQ0GFKAbTPtkNKUbiwAG0YaTfsIBxmyV4nlqJugeCR"

# --- Prepare payload ---
payload = f"message={message}&language=english&route=q&numbers={numbers}"

headers = {
    'authorization': api_key,
    'Content-Type': "application/x-www-form-urlencoded",
    'Cache-Control': "no-cache",
}

# --- Send request ---
response = requests.request("POST", url, data=payload, headers=headers)

# --- Print response from Fast2SMS ---
print(response.text)
