import os
import feedparser
import json
import re
from bs4 import BeautifulSoup
import uuid
from datetime import datetime
import time
import requests

# Get Google credentials from environment variables (GitHub Secrets)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID", "")

# رابط خلاصة RSS لموقع تعيينات العراق
RSS_URL = 'https://www.t9iq.com/feeds/posts/default?alt=rss'

# مسار مجلد الشعارات
LOGOS_DIR = "logos"
if not os.path.exists(LOGOS_DIR):
    os.makedirs(LOGOS_DIR)

# رابط GitHub المباشر لتحميل الصور في التطبيق
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/fi1993rastvbox-design/iraq-jobs-data/main/logos"

# قاموس الشعارات الذكي: يربط الكلمة المفتاحية في العنوان برابط صورة الشعار الرسمي
LOGOS_DICTIONARY = {
    'الداخلية': 'https://upload.wikimedia.org/wikipedia/commons/4/4e/Iraqi_Ministry_of_Interior_logo.png',
    'الدفاع': 'https://upload.wikimedia.org/wikipedia/ar/5/5e/Iraqi_Ministry_of_Defense_logo.png',
    'النفط': 'https://upload.wikimedia.org/wikipedia/ar/0/05/Iraqi_Ministry_of_Oil_logo.png',
    'التربية': 'https://upload.wikimedia.org/wikipedia/ar/thumb/5/52/Iraqi_Ministry_of_Education_logo.png/400px-Iraqi_Ministry_of_Education_logo.png',
    'التعليم العالي': 'https://upload.wikimedia.org/wikipedia/ar/thumb/f/fa/Iraqi_Ministry_of_Higher_Education_and_Scientific_Research_logo.svg/400px-Iraqi_Ministry_of_Higher_Education_and_Scientific_Research_logo.svg.png',
    'الصحة': 'https://upload.wikimedia.org/wikipedia/ar/thumb/1/1a/Iraqi_Ministry_of_Health_logo.png/400px-Iraqi_Ministry_of_Health_logo.png',
    'الكهرباء': 'https://upload.wikimedia.org/wikipedia/ar/thumb/1/12/Iraqi_Ministry_of_Electricity_logo.png/400px-Iraqi_Ministry_of_Electricity_logo.png',
    'الاتصالات': 'https://upload.wikimedia.org/wikipedia/ar/thumb/6/6a/Iraqi_Ministry_of_Communications_logo.png/400px-Iraqi_Ministry_of_Communications_logo.png',
    'مجلس الخدمة': 'https://fpsc.gov.iq/wp-content/uploads/2021/04/logo.png',
    'الحشد الشعبي': 'https://upload.wikimedia.org/wikipedia/ar/thumb/8/8d/Popular_Mobilization_Forces_%28Iraq%29_logo.svg/400px-Popular_Mobilization_Forces_%28Iraq%29_logo.svg.png',
    'مكافحة الارهاب': 'https://upload.wikimedia.org/wikipedia/ar/thumb/0/0c/Iraqi_Counter_Terrorism_Service_logo.png/400px-Iraqi_Counter_Terrorism_Service_logo.png',
    'امانة بغداد': 'https://upload.wikimedia.org/wikipedia/ar/thumb/0/0e/Amanat_Baghdad_logo.png/400px-Amanat_Baghdad_logo.png',
    'وزارة العدل': 'https://upload.wikimedia.org/wikipedia/ar/thumb/e/e4/Iraqi_Ministry_of_Justice_logo.png/400px-Iraqi_Ministry_of_Justice_logo.png',
    'جامعة بغداد': 'https://upload.wikimedia.org/wikipedia/ar/thumb/1/1a/University_of_Baghdad_logo.png/400px-University_of_Baghdad_logo.png',
    'الجامعة المستنصرية': 'https://upload.wikimedia.org/wikipedia/ar/thumb/4/44/Mustansiriyah_University_logo.png/400px-Mustansiriyah_University_logo.png',
    'الجامعة التكنولوجية': 'https://upload.wikimedia.org/wikipedia/ar/thumb/2/23/University_of_Technology%2C_Iraq_logo.png/400px-University_of_Technology%2C_Iraq_logo.png',
    'جامعة البصرة': 'https://upload.wikimedia.org/wikipedia/ar/thumb/1/1a/University_of_Basrah_logo.png/400px-University_of_Basrah_logo.png',
    'جامعة الموصل': 'https://upload.wikimedia.org/wikipedia/ar/thumb/2/25/University_of_Mosul_logo.png/400px-University_of_Mosul_logo.png'
}

# الجمل الإعلانية التي يجب مسحها تلقائياً من النص
SPAM_PHRASES = [
    "انتباه: عند نشر اي وظائف حكومية أو اهلية جديدة سيتم اعلامكم",
    "ليصلك جميع اخبار التعيينات تابعنا",
    "قناتنا في التليكرام",
    "قناتنا في الواتساب",
    "قناتنا في الفايبر",
    "قناتنا في الانستغرام",
    "فيس بوك",
    "انستقرام",
    "تيك توك",
    "لينكد إن",
    "يوزر التليكرام للجهات الراغبة بالنشر",
    "موقعنا الرسمي",
    "اضغط هنا",
    "إدارة موقع تعيينات العراق",
    "مع تمنياتنا بالتوفيق للجميع"
]

def download_and_save_image(image_url):
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            ext = 'png' if 'png' in response.headers.get('Content-Type', '') else 'jpg'
            filename = f"{uuid.uuid4().hex[:12]}.{ext}"
            filepath = os.path.join(LOGOS_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            # إرجاع رابط الجيت هاب المباشر لتلك الصورة
            return f"{GITHUB_RAW_BASE}/{filename}"
    except Exception as e:
        print(f"فشل تحميل الصورة ({image_url}): {e}")
    return None

def get_logo_for_job(title, description):
    combined_text = f"{title} {description}"
    
    # البحث في القاموس أولاً عن اسم الوزارة أو المؤسسة
    for keyword, logo_url in LOGOS_DICTIONARY.items():
        if keyword in combined_text:
            saved_url = download_and_save_image(logo_url)
            if saved_url: return saved_url
            return logo_url 
            
    # محاولة جلب شعار من Google Custom Search API
    if GOOGLE_API_KEY and SEARCH_ENGINE_ID:
        try:
            entity_keywords = ['وزارة', 'جامعة', 'كلية', 'شركة', 'دائرة', 'مستشفى', 'مديرية', 'مصرف', 'هيئة', 'نقابة', 'معهد', 'مركز', 'مؤسسة', 'مجمع', 'صيدلية', 'مختبر', 'مدرسة']
            search_query = None
            
            # البحث عن اسم الشركة في النص المدمج (العنوان + التفاصيل)
            words = combined_text.split()
            for i, word in enumerate(words):
                if word in entity_keywords:
                    # نأخذ الكلمة المفتاحية مع الكلمتين التي تليها كاسم للجهة
                    entity_name = ' '.join(words[i:i+3])
                    search_query = f"شعار {entity_name} العراق"
                    break
                    
            # إذا لم يتم إيجاد اسم جهة محدد، نعتمد على كلمات العنوان الأولى
            if not search_query:
                title_words = title.split()
                short_title = ' '.join(title_words[:4]) if len(title_words) >= 4 else title
                search_query = f"شعار {short_title} العراق"
                
            # استدعاء API لجوجل
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'q': search_query,
                'cx': SEARCH_ENGINE_ID,
                'key': GOOGLE_API_KEY,
                'searchType': 'image',
                'num': 1
            }
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if 'items' in data and len(data['items']) > 0:
                    item = data['items'][0]
                    # نفضل الصورة المصغرة لتجنب الأحجام الكبيرة
                    image_url = item.get('image', {}).get('thumbnailLink') or item.get('link')
                    if image_url:
                        saved_url = download_and_save_image(image_url)
                        if saved_url:
                            return saved_url
        except Exception as e:
            print(f"فشل جلب الصورة من جوجل لـ {title}: {e}")
    
    # الصورة الافتراضية للتطبيق بناءً على طلب المستخدم في حالة عدم العثور على شعار
    return 'https://i.ibb.co/qM1b00XS/dfdfd2c9e13b.png'

def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # معالجة الروابط
    for a in soup.find_all('a'):
        text_a = a.get_text()
        href = a.get('href', '')
        
        # الكشف عن روابط السوشيال ميديا والإعلانات من خلال النص أو الرابط
        is_social_text = any(word in text_a for word in ['تليكرام', 'واتساب', 'فايبر', 'انستغرام', 'فيس بوك', 'قناتنا', 'يوزر', 'تابعنا', 'الرئيسية'])
        is_social_url = any(domain in href.lower() for domain in ['facebook.com', 'instagram.com', 't.me', 'tiktok.com', 'linkedin.com', 'twitter.com', 'youtube.com', 'wa.me', 'whatsapp.com', 'viber.com', 'bit.ly'])
        is_image_link = any(img_ext in href.lower() for img_ext in ['.jpg', '.png', '.jpeg', '.gif', 'blogger.googleusercontent.com/img/'])
        is_main_page = href.strip('/') in ['https://www.t9iq.com', 'http://www.t9iq.com', 'https://t9iq.com', 'http://t9iq.com']
        
        if is_social_text or is_social_url or is_image_link or is_main_page or not href:
            a.decompose()
        else:
            link_text = text_a.strip() if text_a.strip() else "رابط"
            a.replace_with(f" {link_text} \n [الرابط: {href}] \n")
                
    # معالجة النماذج المضمنة (iframes) مثل نماذج جوجل
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        if src and ('docs.google.com/forms' in src or 'form' in src.lower()):
            iframe.replace_with(f" استمارة التقديم (نموذج مضمن) \n [الرابط: {src}] \n")
        else:
            iframe.decompose()
            
    # استخراج النص الصافي
    text = soup.get_text(separator="\n").strip()
    
    # تنظيف الكلمات الإعلانية
    for spam in SPAM_PHRASES:
        text = re.sub(rf"{spam}.*", "", text, flags=re.IGNORECASE)
        text = text.replace(spam, "")
        
    # تنظيف إضافي للأسطر العشوائية
    lines = []
    for line in text.split('\n'):
        clean_line = line.strip()
        # مسح الأسطر التي تحتوي فقط على نقاط أو رموز، أو بقايا الإعلانات المزعجة
        if not clean_line or set(clean_line) <= set('. -_/') or 'قنواتنا' in clean_line or 'انتباه/' in clean_line or 'انتباه:' in clean_line or 'مثبتة في الاسفل' in clean_line or 'مثبتة في الأسفل' in clean_line:
            continue
        # مسح الكلمات الإعلانية المعزولة في سطر لوحدها
        if clean_line in ['التليكرام', 'الواتساب', 'الفايبر', 'الانستغرام', 'أو في', 'او في', 'بالضغط هنا', 'اضغط هنا', 'يوزر التليكرام']:
            continue
        lines.append(clean_line)
        
    return "\n".join(lines)

def fetch_and_parse_jobs():
    print("جاري جلب الوظائف من الـ RSS...")
    feed = feedparser.parse(RSS_URL)
    
    jobs_list = []
    
    # نأخذ أحدث 30 وظيفة فقط كي لا يصبح الملف ضخماً جداً
    for entry in feed.entries[:30]:
        title = entry.title
        link = entry.link
        
        # استخراج التاريخ بصيغة بسيطة
        pub_date_raw = entry.published_parsed
        if pub_date_raw:
            pub_date = datetime(*pub_date_raw[:6]).strftime("%Y-%m-%d %H:%M")
        else:
            pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            
        category = entry.category if 'category' in entry else "الكل"
        
        # تنظيف المحتوى واستخراج اللوجو الذكي
        raw_description = entry.description
        clean_description = clean_html_content(raw_description)
        logo_url = get_logo_for_job(title, clean_description)
        
        job = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "link": link,
            "description": clean_description,
            "pubDate": pub_date,
            "category": category,
            "imageUrl": logo_url
        }
        
        jobs_list.append(job)
        
    return jobs_list

def main():
    import os
    from telegram_scraper import fetch_telegram_jobs, is_duplicate
    
    # تحميل الوظائف المنشورة حالياً (إذا وجد الملف) لتجنب التكرار
    existing_active_jobs = []
    if os.path.exists('jobs.json'):
        try:
            with open('jobs.json', 'r', encoding='utf-8') as f:
                existing_active_jobs = json.load(f)
        except Exception as e:
            print(f"تنبيه: فشل قراءة jobs.json: {e}")
            
    # تحميل الوظائف المعلقة حالياً (إذا وجد الملف) لكي لا نحذفها
    existing_pending_jobs = []
    if os.path.exists('pending_jobs.json'):
        try:
            with open('pending_jobs.json', 'r', encoding='utf-8') as f:
                existing_pending_jobs = json.load(f)
        except Exception as e:
            print(f"تنبيه: فشل قراءة pending_jobs.json: {e}")

    # أولاً جلب وظائف الموقع (RSS)
    rss_jobs = fetch_and_parse_jobs()
    
    # ثانياً جلب وظائف التليجرام
    telegram_jobs = fetch_telegram_jobs(existing_jobs=rss_jobs)
    
    # دمج الوظائف الجديدة المسحوبة
    scraped_jobs = rss_jobs + telegram_jobs
    
    # تصفية الوظائف الجديدة: نقبل فقط الوظائف التي ليست مكررة في jobs.json وليست مكررة في pending_jobs.json
    new_filtered_jobs = []
    for job in scraped_jobs:
        # فحص إذا كانت مكررة في الوظائف المنشورة أو في المعلقة حالياً
        if not is_duplicate(job['title'], job['description'], existing_active_jobs) and \
           not is_duplicate(job['title'], job['description'], existing_pending_jobs) and \
           not is_duplicate(job['title'], job['description'], new_filtered_jobs):
            new_filtered_jobs.append(job)

    # دمج الوظائف المعلقة القديمة مع الوظائف الجديدة المفلترة
    updated_pending_jobs = existing_pending_jobs + new_filtered_jobs
    
    # ترتيب الوظائف المعلقة تنازلياً حسب التاريخ لضمان ظهور الأحدث في البداية
    updated_pending_jobs.sort(key=lambda x: x['pubDate'], reverse=True)
    
    # حفظ الملف كـ JSON في pending_jobs.json
    output_file = 'pending_jobs.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(updated_pending_jobs, f, ensure_ascii=False, indent=4)
        
    print(f"تم بنجاح جلب وتنظيف {len(rss_jobs)} من الموقع و {len(telegram_jobs)} من التليجرام.")
    print(f"الوظائف الجديدة غير المكررة المضافة للمعلقات: {len(new_filtered_jobs)}")
    print(f"العدد الكلي للوظائف المعلقة المحفوظة في {output_file} هو: {len(updated_pending_jobs)}")

if __name__ == "__main__":
    main()
