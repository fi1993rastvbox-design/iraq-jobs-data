import os
import re
import uuid
import json
from datetime import datetime
from difflib import SequenceMatcher
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from dotenv import load_dotenv

load_dotenv()

# قنوات التليجرام التي سيتم السحب منها
CHANNELS = [
    'muhanned_job', 
    'iraq1jops', 
    'mahdi1992lawer', 
    'enghmad88', 
    'biomedicaljobs96'
]

# القنوات المخصصة لوظائف بغداد فقط (أضف معرف القناة هنا)
BAGHDAD_SPECIFIC_CHANNELS = [
    'iraq1jops' # كمثال، يمكنك تعديله إذا كانت قناة أخرى
]

# قائمة المحافظات للبحث عنها في النص
PROVINCES = [
    'بغداد', 'البصرة', 'نينوى', 'أربيل', 'النجف', 'ذي قار', 
    'كركوك', 'الأنبار', 'ديالى', 'المثنى', 'الديوانية', 'ميسان', 
    'واسط', 'صلاح الدين', 'دهوك', 'السليمانية', 'بابل', 'كربلاء'
]

# كلمات تدل على القطاع الحكومي
GOV_KEYWORDS = [
    'وزارة', 'مديرية', 'هيئة حكومية', 'تعيين مركزي', 
    'مجلس الخدمة', 'بصفة عقد', 'بصفة اجور يومية', 'دائرة'
]

# كلمات يجب أن تتوفر لكي نعتبر الخبر "وظيفة" (الفلترة)
JOB_KEYWORDS = [
    'مطلوب', 'تعيين', 'وظائف', 'توظيف', 'فرصة عمل', 'شواغر', 'يعلن'
]

# كلمات سياسية/عامة (إذا وجدت نتجاهل الخبر)
SPAM_POLITICAL_KEYWORDS = [
    'عاجل', 'انفجار', 'سياسة', 'مجلس النواب', 'رئيس الوزراء', 
    'البرلمان', 'تصريح', 'مظاهرات', 'حريق'
]

def is_job_post(text):
    if not text: return False
    # تجاهل الأخبار السياسية أو العامة
    for spam in SPAM_POLITICAL_KEYWORDS:
        if spam in text:
            # استثناء: إذا كان يحتوي على خبر توظيف من رئيس الوزراء مثلاً
            if not any(job_kw in text for job_kw in JOB_KEYWORDS):
                return False
                
    # يجب أن يحتوي على كلمة واحدة على الأقل تدل على التوظيف
    for kw in JOB_KEYWORDS:
        if kw in text:
            return True
    return False

def determine_sector(text):
    for kw in GOV_KEYWORDS:
        if kw in text:
            return 'حكومي'
    return 'أهلي'

def extract_location(text, channel_name, sector):
    # محاولة إيجاد اسم المحافظة في النص
    for province in PROVINCES:
        if province in text:
            return province
            
    # تطبيق قاعدة القنوات المخصصة لبغداد
    if channel_name in BAGHDAD_SPECIFIC_CHANNELS and sector == 'أهلي':
        return 'بغداد'
        
    return 'الكل' # إذا لم يجد شيء

def is_duplicate(new_title, existing_jobs, threshold=0.7):
    # مقارنة العنوان الجديد مع عناوين الوظائف الموجودة لمنع التكرار
    for job in existing_jobs:
        ratio = SequenceMatcher(None, new_title, job['title']).ratio()
        if ratio >= threshold:
            return True
    return False

def extract_title(text):
    # نأخذ أول سطر كعنوان، مع التأكد أنه ليس طويلاً جداً
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        title = lines[0]
        if len(title) > 100:
            return title[:97] + "..."
        return title
    return "فرصة عمل جديدة"

def fetch_telegram_jobs(existing_jobs=[]):
    api_id = os.getenv('TG_API_ID')
    api_hash = os.getenv('TG_API_HASH')
    phone = os.getenv('TG_PHONE')
    
    if not api_id or not api_hash:
        print("تنبيه: لم يتم العثور على إعدادات التليجرام (TG_API_ID, TG_API_HASH) في ملف .env. سيتم تخطي سحب التليجرام.")
        return []

    print("جاري الاتصال بحساب التليجرام لسحب الأخبار بصمت...")
    # إنشاء اتصال (سيقوم بإنشاء ملف session محلي)
    client = TelegramClient('jobs_scraper_session', api_id, api_hash)
    
    new_jobs = []
    try:
        client.start(phone=phone)
        
        for channel in CHANNELS:
            print(f"جاري السحب من قناة: {channel}")
            try:
                # سحب آخر 10 منشورات من القناة
                history = client(GetHistoryRequest(
                    peer=channel,
                    offset_id=0,
                    offset_date=None,
                    add_offset=0,
                    limit=10,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))
                
                for message in history.messages:
                    if not message.message: continue
                    
                    text = message.message
                    
                    # التحقق إذا كان الخبر وظيفة وليس خبراً عاماً
                    if not is_job_post(text):
                        continue
                        
                    title = extract_title(text)
                    
                    # الفحص ضد التكرار
                    if is_duplicate(title, existing_jobs) or is_duplicate(title, new_jobs):
                        continue
                        
                    sector = determine_sector(text)
                    location = extract_location(text, channel, sector)
                    
                    # تنظيف النص (إزالة الروابط ومعرفات التليجرام)
                    clean_desc = re.sub(r'http\S+', '', text)
                    clean_desc = re.sub(r'@\w+', '', clean_desc)
                    clean_desc = clean_desc.replace('قناتنا', '').replace('تابعنا', '')
                    
                    # دمج القطاع والمحافظة في العنوان (اختياري) أو تعيين التصنيف
                    category = f"{sector} - {location}" if location != 'الكل' else sector
                    
                    job = {
                        "id": str(uuid.uuid4())[:8],
                        "title": title,
                        "link": f"https://t.me/{channel}/{message.id}",
                        "description": clean_desc.strip(),
                        "pubDate": message.date.strftime("%Y-%m-%d %H:%M"),
                        "category": category,
                        "location": location, # يمكن استخدامه في الفلتر المباشر
                        "imageUrl": "https://cdn-icons-png.flaticon.com/512/2830/2830305.png" if sector == 'أهلي' else "https://cdn-icons-png.flaticon.com/512/8291/8291079.png"
                    }
                    
                    new_jobs.append(job)
                    
            except Exception as e:
                print(f"خطأ أثناء السحب من القناة {channel}: {e}")
                
    except Exception as e:
         print(f"خطأ في الاتصال بالتليجرام: {e}")
    finally:
        client.disconnect()
        
    print(f"تم سحب {len(new_jobs)} وظيفة جديدة وفريدة من التليجرام.")
    return new_jobs

if __name__ == "__main__":
    jobs = fetch_telegram_jobs()
    for j in jobs:
        print(f"- {j['title']} | {j['category']} | {j['location']}")
