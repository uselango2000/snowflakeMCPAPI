import json
import requests
import boto3
import time

def runDataStream():
    # OpenWeatherMap API setup
    api_key = '2350f4a89bb568d607f98a845de07bc7'  # Replace with your API key
    city = 'New York'
    url = 'https://api.openweathermap.org/data/2.5/weather?q=London,uk&APPID=2350f4a89bb568d607f98a845de07bc7'

    # Create a Kinesis client using boto3
    client = boto3.client('kinesis', region_name='us-east-1')  # Specify the AWS region

    counter = 0
    samples = []

    # Fetch and send data in a loop (simulate real-time)
    for i in range(5):  # Fetch 5 times for demo; adjust as needed
        try:
            print(f"Fetching weather data for {city} (iteration {i+1})...")
            response = requests.get(url)
            if response.status_code == 200:
                weather_data = response.json()
                samples.append(weather_data)
                print(f"Sample #{i+1}: {json.dumps(weather_data, indent=2)}\n")
            else:
                print(f"Failed to fetch weather data: {response.status_code}")
                print(response.text)
        except Exception as e:
            print("Exception occurred:", e)
        time.sleep(2)  # Wait 2 seconds before next fetch (simulate real-time)

    print("Displayed first 5 sample records fetched from API. Pausing for review...")
    input("Press Enter to continue sending data to Kinesis...")

    # Send the fetched samples to Kinesis
    for idx, weather_data in enumerate(samples, 1):
        try:
            kinesis_response = client.put_record(
                StreamName="elanStreamDemo",
                Data=json.dumps(weather_data),
                PartitionKey=str(weather_data.get('dt', int(time.time())))
            )
            counter += 1
            print(f'Message sent #{counter}')
            if kinesis_response['ResponseMetadata']['HTTPStatusCode'] != 200:
                print('Error sending to Kinesis!')
                print(kinesis_response)
        except Exception as e:
            print(f"Exception occurred while sending sample #{idx}:", e)

    print('All messages sent successfully!')
    return counter

def main():
    print("Starting to fetch and display real-time weather data samples from API...")
    runDataStream()

if __name__ == "__main__":
    main()