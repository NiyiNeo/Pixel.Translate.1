# Pixel Translate: Automated Audio Translation Pipeline

Pixel Translate is an automated CI/CD pipeline that processes uploaded `.mp3` audio files by transcribing, translating, and converting them back into speech using AWS services. This project demonstrates a serverless approach to building multilingual media content powered by GitHub Actions and AWS.

## Features

- 🎙 **Audio Transcription** – Uses Amazon Transcribe to convert spoken language into text.
- 🌐 **Language Translation** – Translates the transcription into a target language using Amazon Translate.
- 🗣 **Speech Synthesis** – Converts translated text into speech using Amazon Polly.
- ☁️ **S3 Bucket Integration** – Manages input, intermediate, and output files using structured prefixes in S3.
- ⚙️ **CI/CD Automation** – GitHub Actions handle:
  - `on_pull_request`: Triggers beta test using the beta bucket for S3.
  - `on_merge_to_main`: Triggers production pipeline with finalized output prod bucket for S3.
- 🔒 **Secure Environment** – All AWS credentials and runtime variables are managed with GitHub Secrets.

---

## Architecture

1. **User uploads an audio file** to GitHub and creates a pull request.
2. **GitHub Actions triggers** a workflow:
   - Uploads audio to an S3 bucket
   - Starts a transcription job via Amazon Transcribe
   - Downloads the resulting transcript from S3
   - Translates the text using Amazon Translate
   - Synthesizes the translated text to speech with Amazon Polly
   - Uploads final audio to S3 production or beta path based on environment
3. **Artifacts (text + audio)** are stored in structured paths in S3:
   - `prod/audio/` → Input audio
   - `beta/transcripts/` → Raw transcriptions
   - `beta/translations/` → Translated text
   - `prod/audio_outputs/` → Final multilingual audio

---

## AWS Services Used

- **Amazon S3** – Stores input, intermediate, and output files
- **Amazon Transcribe** – Converts speech to text
- **Amazon Translate** – Translates text between languages
- **Amazon Polly** – Synthesizes translated text into speech
- **IAM** – Manages role-based access for secure automation

---

## Folder Structure

```bash
.
├── .github
│   └── workflows
│       ├── on_pull_request.yml     # Triggers on PR to test in beta
│       └── on_merge.yml            # Triggers on merge to main (prod)
├── process_audio.py                # Core processing script
├── README.md                       # Project documentation
└── pixel.language.mp3              # Example input audio file
