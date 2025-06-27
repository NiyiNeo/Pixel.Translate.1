import boto3
import os
import json
import time
import requests 
from datetime import datetime

# Setup AWS session using GitHub Actions secrets
session = boto3.Session(
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name=os.environ['AWS_REGION']
)

# AWS clients
s3 = session.client('s3')
transcribe = session.client('transcribe')
translate = session.client('translate')
polly = session.client('polly')

#GitHub secrets
prod_bucket = os.environ['S3_BUCKET_PROD']
beta_bucket = os.environ['S3_BUCKET_BETA']
filename = os.environ['FILENAME']
source_lang = os.environ['SOURCE_LANG']
translate_lang = os.environ['TRANSLATE_LANG']
polly_voice = os.environ['POLLY_VOICE']

# Paths and timestamp
timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
job_name = f"PixelLearn-{timestamp}"
audio_file = f"prod/audio/{filename}.mp3"
audio_uri = f"s3://{prod_bucket}/{audio_file}"
transcript_key = f"beta/transcripts/{filename}.txt"
translated_key = f"beta/translations/{filename}_{translate_lang}.txt"
final_audio_key = f"prod/audio_outputs/{filename}_{translate_lang}.mp3"

# Step 1: Upload audio to S3
s3.upload_file(f"{filename}.mp3", prod_bucket, audio_file)

# Step 2: Start transcription job
transcribe.start_transcription_job(
    TranscriptionJobName=job_name,
    Media={'MediaFileUri': audio_uri},
    MediaFormat='mp3',
    LanguageCode=source_lang,
    OutputBucketName=beta_bucket
)

# Step 3: Wait for job to finish
while True:
    status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    job_status = status['TranscriptionJob']['TranscriptionJobStatus']
    if job_status in ['COMPLETED', 'FAILED']:
        if job_status == 'FAILED':
            raise Exception("Transcription failed.")
        break
    time.sleep(5)

# Step 4: Get transcript file URI
transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
transcript_json = json.loads(requests.get(transcript_uri).text)
transcript_text = transcript_json['results']['transcripts'][0]['transcript']

# Step 5: Upload plain transcript
s3.put_object(Bucket=beta_bucket, Key=transcript_key, Body=transcript_text.encode())

# Step 6: Translate
translation = translate.translate_text(
    Text=transcript_text,
    SourceLanguageCode=source_lang.split("-")[0],
    TargetLanguageCode=translate_lang
)
translated_text = translation['TranslatedText']

# Step 7: Upload translated text
s3.put_object(Bucket=beta_bucket, Key=translated_key, Body=translated_text.encode())

# Step 8: Use Polly to synthesize speech
polly_response = polly.synthesize_speech(
    OutputFormat='mp3',
    Text=translated_text,
    VoiceId=polly_voice,
    LanguageCode=f"{translate_lang}-ES"
)

with open(f"{filename}_{translate_lang}.mp3", 'wb') as f:
    f.write(polly_response['AudioStream'].read())

# Step 9: Upload final audio
s3.upload_file(f"{filename}_{translate_lang}.mp3", prod_bucket, final_audio_key)


