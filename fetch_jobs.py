import os
import feedparser
import json
import re
from bs4 import BeautifulSoup
import uuid
from datetime import datetime
import time
import requests


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
    'جامعة الموصل': 'https://upload.wikimedia.org/wikipedia/ar/thumb/2/25/University_of_Mosul_logo.png/400px-University_of_Mosul_logo.png',
    'شركة زين': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Zain_Group_logo.svg/200px-Zain_Group_logo.svg.png',
    'اسيا سيل': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Asiacell_Logo.svg/200px-Asiacell_Logo.svg.png',
    'آسيا سيل': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Asiacell_Logo.svg/200px-Asiacell_Logo.svg.png',
    'كورك': 'https://upload.wikimedia.org/wikipedia/ar/thumb/9/91/Korek_Telecom_logo.png/200px-Korek_Telecom_logo.png',
    'مصرف الرافدين': 'https://upload.wikimedia.org/wikipedia/ar/8/87/Rafidain_Bank_Logo.png',
    'مصرف الرشيد': 'https://rasheedbank.gov.iq/wp-content/uploads/2021/08/logo.png',
    'المصرف العراقي للتجارة': 'https://upload.wikimedia.org/wikipedia/en/thumb/f/f6/Trade_Bank_of_Iraq_logo.png/220px-Trade_Bank_of_Iraq_logo.png',
    'كي كارد': 'https://upload.wikimedia.org/wikipedia/ar/thumb/6/67/Qi_Card_logo.svg/200px-Qi_Card_logo.svg.png',
    'جامعة الفراهيدي': 'https://upload.wikimedia.org/wikipedia/ar/4/47/Al-Farahidi_University_logo.png',
    'كلية التراث': 'https://upload.wikimedia.org/wikipedia/ar/b/ba/Al-Turath_University_College_logo.png',
    'جامعة المستقبل': 'https://upload.wikimedia.org/wikipedia/ar/a/a2/Al-Mustaqbal_University_College_logo.png',
    'جامعة الكفيل': 'https://upload.wikimedia.org/wikipedia/ar/5/52/Al-Kafeel_University_logo.png',
    'جامعة العميد': 'https://upload.wikimedia.org/wikipedia/ar/7/7b/Al-Ameed_University_logo.png',
    'هيئة النزاهة': 'https://upload.wikimedia.org/wikipedia/ar/thumb/4/42/Commission_of_Integrity_%28Iraq%29_logo.png/200px-Commission_of_Integrity_%28Iraq%29_logo.png',
    'الوقف الشيعي': 'https://upload.wikimedia.org/wikipedia/ar/thumb/f/fd/Shiite_Endowment_Bureau_logo.png/200px-Shiite_Endowment_Bureau_logo.png',
    'الوقف السني': 'https://upload.wikimedia.org/wikipedia/ar/thumb/e/e6/Sunni_Endowment_Bureau_logo.png/200px-Sunni_Endowment_Bureau_logo.png'
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
    "مع تمنياتنا بالتوفيق للجميع",
    "مكتب اليمان",
    "لتجنب الاخطاء ولضمان التقديم الصحيح",
    "مراجعة المكتب الرسمي والممثل الوحيد",
    "للدخول إلى المنصات الرسمية الخاصة بمكتب",
    "الاتصال بالمكتب على الارقام التالية",
    "اثناء اوقات الدوام الرسمي",
    "المكتب الرسمي ل موقع تعيينات العراق",
    "المكتب الرسمي لموقع تعيينات العراق",
    "مكتب اليمان للتقديم",
    "#علي_احمد_الجنابي",
    "علي احمد الجنابي",
    "علي_احمد_الجنابي"
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
            
    # محاولة جلب شعار عبر محرك بحث DuckDuckGo المجاني
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
            
        # استخدام Google Custom Search للبحث عن الصورة
        time.sleep(1.0)
        api_key = os.environ.get("GOOGLE_API_KEY")
        cx = os.environ.get("SEARCH_ENGINE_ID")
        
        if api_key and cx:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "q": search_query,
                "cx": cx,
                "key": api_key,
                "searchType": "image",
                "num": 1,
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                results = response.json()
                if "items" in results and len(results["items"]) > 0:
                    image_url = results["items"][0]["link"]
                    saved_url = download_and_save_image(image_url)
                    if saved_url:
                        return saved_url
            else:
                print(f"Google API Error: {response.status_code} - {response.text}")
        else:
            print("مفاتيح Google API غير متوفرة في البيئة.")
    except Exception as e:
        print(f"فشل جلب الصورة من Google لـ {title}: {e}")
    
    # الصورة الافتراضية للتطبيق تم إزالتها واستبدالها برمجياً داخل التطبيق لتجنب مشاكل الروابط
    return None

def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # معالجة الروابط
    for a in soup.find_all('a'):
        text_a = a.get_text()
        href = a.get('href', '')
        
        # الكشف عن روابط السوشيال ميديا الإعلانية فقط وتجنب مسح روابط التقديم للشركات
        is_promo_text = any(word in text_a for word in ['قناتنا', 'تابعنا', 'الرئيسية', 'اشترك', 'يوزر التليكرام للجهات'])
        is_promo_url = any(domain in href.lower() for domain in ['youtube.com', 'tiktok.com', 'snapchat.com'])
        is_main_page = href.strip('/') in ['https://www.t9iq.com', 'http://www.t9iq.com', 'https://t9iq.com', 'http://t9iq.com']
        
        # تجنب حذف الروابط الخاصة بالتقديم (t.me, wa.me, viber, forms, etc.)
        if is_promo_text or is_promo_url or is_main_page or not href:
            a.decompose()
        else:
            link_text = text_a.strip() if text_a.strip() else "رابط"
            a.replace_with(f" {link_text} [الرابط: {href}] ")
                
    # معالجة النماذج المضمنة (iframes) مثل نماذج جوجل
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        if src and ('docs.google.com/forms' in src or 'form' in src.lower()):
            iframe.replace_with(f" استمارة التقديم (نموذج مضمن) \n [الرابط: {src}] \n")
        else:
            iframe.decompose()
            
    # استخراج النص الصافي
    text = soup.get_text(separator="\n").strip()
    
    # حذف الإعلانات التي تأتي في نهاية المنشور بالكامل (مثل إعلانات مكاتب التقديم)
    footer_spams = [
        'مكتب اليمان', 'المكتب الرسمي ل موقع', 'المكتب الرسمي لموقع', 
        'إدارة موقع تعيينات', 'لتجنب الاخطاء ولضمان التقديم', 
        'مراجعة المكتب الرسمي', 'المنصات الرسمية الخاصة بمكتب', 
        'الاتصال بالمكتب على الارقام', 'الممثل الوحيد'
    ]
    for footer_spam in footer_spams:
        idx = text.find(footer_spam)
        if idx != -1:
            text = text[:idx] # حذف كل النص الذي يأتي بعد الإعلان
            
    # تنظيف الكلمات الإعلانية العادية في بقية النص
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
        
        # تصحيح القسم للأخبار العامة مثل قرعة الحج التي لا تعتبر وظائف
        job_keywords = ['مطلوب', 'تعيين', 'وظائف', 'توظيف', 'فرصة عمل', 'شواغر', 'يعلن', 'بحاجة']
        is_job = any(kw in title for kw in job_keywords)
        if any(word in title for word in ['حج', 'عمرة', 'الحج', 'العمرة']) and not is_job:
            category = 'أخبار'
            
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

def filter_old_jobs(jobs, max_days=180):
    filtered = []
    now = datetime.now()
    for job in jobs:
        try:
            job_date = datetime.strptime(job['pubDate'].split(' ')[0], "%Y-%m-%d")
            if (now - job_date).days <= max_days:
                filtered.append(job)
        except Exception:
            filtered.append(job)
    return filtered

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
            
    # تحميل طابور الإشعارات الحالي (إذا وجد) لدمجه
    existing_queue = []
    if os.path.exists('notifications_queue.json'):
        try:
            with open('notifications_queue.json', 'r', encoding='utf-8') as f:
                existing_queue = json.load(f)
        except Exception as e:
            print(f"تنبيه: فشل قراءة notifications_queue.json: {e}")

    # أولاً جلب وظائف الموقع (RSS)
    rss_jobs = fetch_and_parse_jobs()
    
    # ثانياً جلب وظائف التليجرام
    telegram_jobs = fetch_telegram_jobs(existing_jobs=rss_jobs)
    
    # دمج الوظائف الجديدة المسحوبة
    scraped_jobs = rss_jobs + telegram_jobs
    
    # تصفية الوظائف الجديدة: نقبل فقط الوظائف التي ليست مكررة في jobs.json
    new_filtered_jobs = []
    for job in scraped_jobs:
        # فحص إذا كانت مكررة في الوظائف المنشورة حالياً
        if not is_duplicate(job['title'], job['description'], existing_active_jobs) and \
           not is_duplicate(job['title'], job['description'], new_filtered_jobs):
            new_filtered_jobs.append(job)

    # دمج الوظائف القديمة مع الوظائف الجديدة المفلترة (الجديدة في البداية)
    updated_jobs = new_filtered_jobs + existing_active_jobs
    
    # تنظيف الوظائف التي مر عليها أكثر من 180 يوماً
    updated_jobs = filter_old_jobs(updated_jobs, 180)
    
    # ترتيب الوظائف تنازلياً حسب التاريخ لضمان ظهور الأحدث في البداية
    updated_jobs.sort(key=lambda x: x['pubDate'], reverse=True)
    
    # حفظ الملف كـ JSON في jobs.json
    with open('jobs.json', 'w', encoding='utf-8') as f:
        json.dump(updated_jobs, f, ensure_ascii=False, indent=4)
        
    # إضافة الوظائف الجديدة إلى طابور الإشعارات
    if new_filtered_jobs:
        updated_queue = existing_queue + new_filtered_jobs
        with open('notifications_queue.json', 'w', encoding='utf-8') as f:
            json.dump(updated_queue, f, ensure_ascii=False, indent=4)
        
    print(f"تم بنجاح جلب وتنظيف {len(rss_jobs)} من الموقع و {len(telegram_jobs)} من التليجرام.")
    print(f"الوظائف الجديدة غير المكررة المضافة والنشر التلقائي: {len(new_filtered_jobs)}")
    print(f"العدد الكلي للوظائف المنشورة في jobs.json هو: {len(updated_jobs)}")

if __name__ == "__main__":
    main()
