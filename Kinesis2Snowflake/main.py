import json
import csv
import boto3

def runDataStream():
    # List to store all the taxi cab ride data
    taxi_cab_rides = []

    # Create a Kinesis client using boto3
    client = boto3.client('kinesis', region_name='us-east-1')  # Specify the AWS region

    # Counter to track the number of messages sent
    counter = 0

    # Open the CSV file containing taxi ride data
    with open('taxi_data.csv', encoding='utf-8') as csv_file:
        # Read the CSV file as a dictionary
        csv_reader = csv.DictReader(csv_file)
        
        # Append each row (ride) to the taxi_cab_rides list
        for row in csv_reader:
            taxi_cab_rides.append(row)

    # Iterate through the list of rides to send each one to the Kinesis stream
    for ride in taxi_cab_rides:
        # Send the ride data to the Kinesis stream
        response = client.put_record(
            StreamName="elanStreamDemo",  # Name of the Kinesis stream
            Data=json.dumps(ride),      # Convert ride data to JSON string
            PartitionKey=str(hash(ride['tpep_pickup_datetime']))  # Use hashed pickup datetime as partition key
        )
        
        # Increment the counter for each sent message
        counter += 1
        print('Message sent #' + str(counter))
        
        # Check if the message was not successfully sent
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            print('Error!')  # Print an error message
            print(response)  # Print the response details
    print('All messages sent successfully!')  # Print success message
    return counter  # Return the total number of messages sent


def main():
    print("Starting to send taxi cab ride data to Kinesis stream...")
    # The main function is where the script starts execution
    # The code above will run when this script is executed directly
    runDataStream()  
    

if __name__ == "__main__":
    main()