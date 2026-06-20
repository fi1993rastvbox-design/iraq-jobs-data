import os
import re
import uuid
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from difflib import SequenceMatcher

# قنوات التليجرام التي سيتم السحب منها
CHANNELS = [
    'muhannad_job', 
    'iraq1jobs', 
    'mahdi1992lawer', 
    'engahmad88', 
    'biomedicaljobs96',
    'baghdadjobss',
    'medical_field'
]

# القنوات المخصصة لوظائف بغداد فقط (أضف معرف القناة هنا)
BAGHDAD_SPECIFIC_CHANNELS = [
    'iraq1jobs',
    'baghdadjobss'
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
    'مطلوب', 'تعيين', 'وظائف', 'توظيف', 'فرصة عمل', 'شواغر', 'يعلن', 'بحاجة'
]

# كلمات سياسية/عامة (إذا وجدت نتجاهل الخبر)
SPAM_POLITICAL_KEYWORDS = [
    'عاجل', 'انفجار', 'سياسة', 'مجلس النواب', 'رئيس الوزراء', 
    'البرلمان', 'تصريح', 'مظاهرات', 'حريق'
]

# كلمات تدل على إعلانات تجارية، إيجار، بيع، أو ترويج للقنوات (يجب تجاهلها)
SPAM_AD_KEYWORDS = [
    'للإيجار', 'للايجار', 'شقة للإيجار', 'شقة للايجار', 'شقق للإيجار', 'شقق للايجار',
    'سيارات للإيجار', 'سيارات للايجار', 'عيادات للإيجار', 'عيادات للايجار',
    'محل للإيجار', 'محل للايجار', 'للبيع', 'بيع وشراء', 'البيع المباشر',
    'نشر اعلاناتكم', 'نشر إعلاناتكم', 'للإعلان في القناة', 'للاعلان في القناة',
    'للاعلان بالقناة', 'للإعلان بالقناة', 'تبادل اعلاني', 'تبادل إعلاني',
    'ترويج لقنواتكم', 'اشتراك بالقناة', 'الاعلان في القناة', 'للإعلان راسل',
    'تأجير', 'تاجير', 'تأجير سيارات', 'تاجير سيارات', 'تأجير السيارات', 'تاجير السيارات'
]

def is_job_post(text):
    if not text: return False
    
    # 1. تجاهل الإعلانات وعروض البيع والإيجار والترويج المزعجة أولاً
    for ad_spam in SPAM_AD_KEYWORDS:
        if ad_spam in text:
            return False
            
    # 2. تجاهل الأخبار السياسية أو العامة
    for spam in SPAM_POLITICAL_KEYWORDS:
        if spam in text:
            # استثناء: إذا كان يحتوي على خبر توظيف من رئيس الوزراء مثلاً
            if not any(job_kw in text for job_kw in JOB_KEYWORDS):
                return False
                
    # 3. يجب أن يحتوي على كلمة واحدة على الأقل تدل على التوظيف
    for kw in JOB_KEYWORDS:
        if kw in text:
            return True
    return False

def determine_sector(text):
    for kw in GOV_KEYWORDS:
        if kw in text:
            return 'القطاع الحكومي العام'
    return 'القطاع الخاص'

def extract_location(text, channel_name, sector):
    # محاولة إيجاد اسم المحافظة في النص
    for province in PROVINCES:
        if province in text:
            return province
            
    # تطبيق قاعدة القنوات المخصصة لبغداد
    if channel_name in BAGHDAD_SPECIFIC_CHANNELS and sector == 'القطاع الخاص':
        return 'بغداد'
        
    return 'الكل' # إذا لم يجد شيء

def clean_telegram_text(text):
    if not text:
        return ""
    
    # 1. إزالة أي روابط سوشيال ميديا (تليجرام، فيسبوك، انستغرام، يوتيوب، إلخ)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'\S+\.com\S*', '', text)
    text = re.sub(r't\.me/\S+', '', text)
    text = re.sub(r'telegram\.me/\S+', '', text)
    
    # 2. إزالة المعرفات التي تبدأ بـ @ (مثل @baghdadjobss)
    text = re.sub(r'@\w+', '', text)
    
    # 3. إزالة العبارات الترويجية والطلب بالاشتراك باللغة العربية
    promo_phrases = [
        r'قناتنا في التليكرام', r'قناتنا في التليجرام', r'قناتنا على التليكرام',
        r'تابعنا على', r'تابعونا على', r'للمزيد انضم إلينا', r'انضم لقناتنا',
        r'رابط القناة', r'اشترك في', r'للاشتراك', r'يوزر التليكرام',
        r'الرقم الوتساب الخاص بنشر الوظائف', r'الرقم الواتساب الخاص بنشر الوظائف',
        r'موقعنا الرسمي', r'صفحتنا على', r'على الفيس بوك', r'على الانستغرام',
        r'على الانستكرام', r'تابعونا', r'اشتركوا', r'للنشر والاعلان',
        r'انستغرام', r'فيس بوك', r'انستكرام', r'تيك توك', r'سناب شات'
    ]
    for promo in promo_phrases:
        text = re.sub(promo + r'.*', '', text, flags=re.IGNORECASE)
        text = re.sub(promo, '', text, flags=re.IGNORECASE)
    
    # 4. إزالة أرقام الهواتف الترويجية الخاصة بالقنوات
    known_promo_numbers = [
        r'0773\s*382\s*3707', r'07733823707'
    ]
    for num in known_promo_numbers:
        text = re.sub(num, '', text)
        
    # 5. تنظيف الرموز والزخارف غير الضرورية والأسطر الفارغة المتعددة
    text = re.sub(r'[\*_-]{3,}', '', text)
    text = re.sub(r'▓+|˹|˼|▒+|░+', '', text)
    
    # تنظيف الأسطر الفارغة الزائدة
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # إزالة الأسطر التي تحتوي فقط على إيموجي أو علامات ترقيم
    clean_lines = []
    for line in lines:
        if len(line) < 3 and not any(c.isalnum() for c in line):
            continue
        clean_lines.append(line)
        
    return "\n".join(clean_lines)

def is_duplicate(new_title, new_desc, existing_jobs, threshold=0.75):
    # مقارنة العنوان والوصف مع الوظائف الموجودة لمنع التكرار
    new_title_clean = re.sub(r'\[.*?\]', '', new_title).strip() # إزالة [المحافظة] للمقارنة العادلة
    
    for job in existing_jobs:
        existing_title_clean = re.sub(r'\[.*?\]', '', job['title']).strip()
        
        # 1. فحص تشابه العنوان
        title_ratio = SequenceMatcher(None, new_title_clean, existing_title_clean).ratio()
        if title_ratio >= 0.85:
            return True
            
        # 2. إذا كان تشابه العنوان متوسطاً، نفحص تشابه الوصف
        if title_ratio >= threshold:
            new_desc_snippet = new_desc[:150].strip()
            existing_desc_snippet = job['description'][:150].strip()
            desc_ratio = SequenceMatcher(None, new_desc_snippet, existing_desc_snippet).ratio()
            if desc_ratio >= 0.7:
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
    new_jobs = []
    
    # رأس طلب المتصفح لتجنب الحظر
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print("جاري سحب منشورات التليجرام عبر المتصفح العام (بدون الحاجة لحساب)...")
    
    for channel in CHANNELS:
        print(f"جاري السحب من صفحة الويب العامة للقناة: {channel}")
        try:
            url = f"https://t.me/s/{channel}"
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"تنبيه: فشل جلب القناة {channel} (رمز الاستجابة: {response.status_code})")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # البحث عن منشورات القناة
            messages = soup.find_all('div', class_='tgme_widget_message')
            
            # نأخذ آخر 10 منشورات
            for message in messages[-10:]:
                text_div = message.find('div', class_='tgme_widget_message_text')
                if not text_div:
                    continue
                    
                text = text_div.get_text(separator='\n')
                
                # التحقق إذا كان الخبر وظيفة وليس خبراً عاماً
                if not is_job_post(text):
                    continue
                
                # تنظيف النص بالكامل أولاً
                clean_desc = clean_telegram_text(text)
                if not clean_desc:
                    continue
                    
                title = extract_title(clean_desc)
                
                # الفحص ضد التكرار
                if is_duplicate(title, clean_desc, existing_jobs) or is_duplicate(title, clean_desc, new_jobs):
                    continue
                    
                sector = determine_sector(text)
                location = extract_location(text, channel, sector)
                
                # إضافة المحافظة في بداية العنوان
                if location != 'الكل':
                    title = f"[{location}] {title}"
                
                # استخراج تاريخ النشر
                date_time = message.find('time', class_='time')
                if date_time and date_time.get('datetime'):
                    raw_date = date_time.get('datetime')
                    try:
                        # تحويل صيغة التاريخ لشيء مقروء
                        iso_date = raw_date.replace('Z', '+00:00')
                        dt = datetime.fromisoformat(iso_date)
                        pub_date = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                else:
                    pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                # استخراج رابط المنشور ورقم المعرف
                date_anchor = message.find('a', class_='tgme_widget_message_date')
                if date_anchor and date_anchor.get('href'):
                    post_link = date_anchor.get('href')
                else:
                    post_link = f"https://t.me/{channel}"
                
                category = sector  # توحيد التصنيفات مع تطبيق الموبايل (القطاع الخاص / القطاع الحكومي العام)
                
                # توليد ID مميز للمنشور
                post_id = str(uuid.uuid4())[:8]
                match = re.search(r'/(\d+)$', post_link)
                if match:
                    post_id = f"tg-{match.group(1)}"
                
                job = {
                    "id": post_id,
                    "title": title,
                    "link": post_link,
                    "description": clean_desc,
                    "pubDate": pub_date,
                    "category": category,
                    "imageUrl": "https://cdn-icons-png.flaticon.com/512/2830/2830305.png" if sector == 'القطاع الخاص' else "https://cdn-icons-png.flaticon.com/512/8291/8291079.png"
                }
                
                new_jobs.append(job)
                
        except Exception as e:
            print(f"خطأ أثناء السحب من القناة {channel}: {e}")
            
    print(f"تم سحب {len(new_jobs)} وظيفة جديدة وفريدة من التليجرام.")
    return new_jobs

if __name__ == "__main__":
    jobs = fetch_telegram_jobs()
    for j in jobs:
        print(f"- {j['title']} | {j['category']}")
