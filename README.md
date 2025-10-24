# 🧠 String Analyzer API

A RESTful API built with **Django** and **Django REST Framework (DRF)** that analyzes strings and stores their computed properties — such as length, palindrome status, word count, character frequency, and hash.

---

## 🚀 Features

For every string analyzed, the API computes and returns:

- ✅ **Length** — total number of characters  
- ✅ **Palindrome check** — determines if the string reads the same backwards  
- ✅ **Unique character count**  
- ✅ **Word count**  
- ✅ **SHA-256 hash**  
- ✅ **Character frequency map**  
- ✅ **Timestamp** of when it was created  

---

## 🛠️ Tech Stack

- **Python 3.13+**
- **Django 5+**
- **Django REST Framework**
- **Gunicorn**
- **WhiteNoise** for serving static files
- **Railway.app** for deployment

---

## 🧩 Project Setup (Local Development)

### 1️⃣ Clone the repository
```bash
git clone https://github.com/mhykeborhlar/string_analyzer.git
cd string_analyzer
pip install -r requirements.txt
python manage.py migrate


Example
{
  "value": "racecar"
}
