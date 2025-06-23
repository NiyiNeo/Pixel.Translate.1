import boto3
import os
import json
import time
from datetime import datetime

# Start session using GitHub Actions secrets
session = boto3.Session(
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name=os.environ['AWS_REGION']
)

# Clients
s3 = session.client('s3')
transcribe = session.client('transcribe')
translate = session.client('translate')
polly = session.client('polly')

# Environment Variables
prod_bucket = os.environ['S3_BUCKET_PROD']
beta_bucket = os.environ['S3_BUCKET_BETA']
filename = os.environ['FILENAME']
source_lang = os.environ['SOURCE_LANG']
translate_lang = os.environ['TRANSLATE_LANG']
polly_voice = os.environ['POLLY_VOICE']

# Prefixes
beta_prefix = "beta"
prod_prefix = "prod"

# Timestamp
timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

# Define keys and paths
audio_file = f"{prod_prefix}/audio/{filename}.mp3"
audio_uri = f"s3://{prod_bucket}/{audio_file}"
transcript_key = f"{beta_prefix}/transcripts/{filename}.txt"
translated_key = f"{beta_prefix}/translations/{filename}_{translate_lang}.txt"
translated_local_file = f"{filename}_{translate_lang}.txt"
final_audio_file = f"{prod_prefix}/audio_outputs/{filename}_{translate_lang}.mp3"

# Step 1: Upload original MP3 to S3
print("Uploading MP3 to S3...")
s3.upload_file(f"{filename}.mp3", prod_bucket, audio_file)
print(f"Uploaded to: {audio_uri}")

# Step 2: Start transcription job
job_name = f"PixelLearn-{timestamp}"
print(f"Starting transcription job: {job_name}")
transcribe.start_transcription_job(
    TranscriptionJobName=job_name,
    Media={'MediaFileUri': audio_uri},
    MediaFormat='mp3',
    LanguageCode=source_lang,
    OutputBucketName=beta_bucket,
    OutputKey=transcript_key
)

# Step 3: Wait for transcription to complete
while True:
    status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    job_status = status['TranscriptionJob']['TranscriptionJobStatus']
    if job_status in ['COMPLETED', 'FAILED']:
        print(f"Transcription job status: {job_status}")
        if job_status == 'FAILED':
            raise Exception("Transcription job failed.")
        break
    print("...waiting for transcription...")
    time.sleep(5)

# Step 4: Download transcript JSON and extract text
transcript_json_key = f"{job_name}.json"
print(f"Downloading transcript from: s3://{beta_bucket}/{transcript_json_key}")
transcript_obj = s3.get_object(Bucket=beta_bucket, Key=transcript_json_key)
transcript_text = json.loads(transcript_obj['Body'].read())['results']['transcripts'][0]['transcript']

# Step 5: Upload plain transcript to S3
print("Uploading transcript text...")
s3.put_object(Bucket=beta_bucket, Key=transcript_key, Body=transcript_text.encode('utf-8'))
print(f"Transcript uploaded to s3://{beta_bucket}/{transcript_key}")

# Step 6: Translate text (realtime)
print("Translating text in real time...")
translation_result = translate.translate_text(
    Text=transcript_text,
    SourceLanguageCode=source_lang.split('-')[0],
    TargetLanguageCode=translate_lang
)
translated_text = translation_result['TranslatedText']

# Step 7: Save translated text locally and to S3
with open(translated_local_file, 'w', encoding='utf-8') as f:
    f.write(translated_text)
print("Local translated file created")

s3.put_object(Bucket=beta_bucket, Key=translated_key, Body=translated_text.encode('utf-8'))
print(f"Translated text uploaded to s3://{beta_bucket}/{translated_key}")

# Step 8: Convert translated text to speech and save locally
print("Synthesizing speech from translated text...")
polly_response = polly.synthesize_speech(
    OutputFormat='mp3',
    Text=translated_text,
    VoiceId=polly_voice,
    LanguageCode=f"{translate_lang}-ES"
)

with open(f"{filename}_{translate_lang}.mp3", 'wb') as f:
    f.write(polly_response['AudioStream'].read())
print("Audio MP3 created locally")

# Step 9: Upload final audio to S3
s3.upload_file(f"{filename}_{translate_lang}.mp3", prod_bucket, final_audio_file)
print(f"Final audio uploaded to s3://{prod_bucket}/{final_audio_file}")

