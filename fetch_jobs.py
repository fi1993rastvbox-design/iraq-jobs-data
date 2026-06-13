import feedparser
import json
import re
from bs4 import BeautifulSoup
import uuid
from datetime import datetime
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None
import time

# رابط خلاصة RSS لموقع تعيينات العراق
RSS_URL = 'https://www.t9iq.com/feeds/posts/default?alt=rss'

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

def get_logo_for_title(title):
    # البحث في القاموس عن اسم الوزارة أو المؤسسة
    for keyword, logo_url in LOGOS_DICTIONARY.items():
        if keyword in title:
            return logo_url
            
    # محاولة جلب شعار من جوجل (عبر DuckDuckGo)
    if DDGS is not None:
        try:
            # استخراج اسم الجهة بذكاء للبحث عن شعارها
            entity_keywords = ['وزارة', 'جامعة', 'كلية', 'شركة', 'دائرة', 'مستشفى', 'مديرية', 'مصرف', 'هيئة', 'نقابة', 'معهد']
            search_query = None
            
            words = title.split()
            for i, word in enumerate(words):
                if word in entity_keywords:
                    # أخذ الكلمة المفتاحية مع الكلمتين التي تليها (مثال: جامعة مدينة العلم)
                    entity_name = ' '.join(words[i:i+3])
                    search_query = f"شعار {entity_name} العراق"
                    break
                    
            # إذا لم نجد كلمة مفتاحية، نستخدم أول 4 كلمات
            if not search_query:
                short_title = ' '.join(words[:4]) if len(words) >= 4 else title
                search_query = f"شعار {short_title} العراق"
                
            with DDGS() as ddgs:
                results = [r for r in ddgs.images(search_query, max_results=1)]
                if results and 'image' in results[0]:
                    time.sleep(1) # لتفادي الحظر
                    return results[0]['image']
        except Exception as e:
            print(f"فشل جلب الصورة لـ {title}: {e}")
    
    # إذا فشل جوجل، نستخدم أيقونات افتراضية مميزة ومخصصة حسب الكلمة المفتاحية
    if 'جامعة' in title or 'كلية' in title or 'معهد' in title:
        return 'https://cdn-icons-png.flaticon.com/512/8074/8074805.png' # أيقونة جامعة رائعة
    if 'مستشفى' in title or 'صحة' in title or 'طبي' in title:
        return 'https://cdn-icons-png.flaticon.com/512/4320/4320337.png' # أيقونة مستشفى
    if 'مصرف' in title or 'بنك' in title:
        return 'https://cdn-icons-png.flaticon.com/512/2830/2830284.png' # أيقونة بنك
    if 'مدرسة' in title or 'تدريس' in title:
        return 'https://cdn-icons-png.flaticon.com/512/2436/2436855.png' # أيقونة مدرسة
    if 'مطار' in title or 'طيران' in title:
        return 'https://cdn-icons-png.flaticon.com/512/3163/3163155.png' # أيقونة طيران
        
    # صورة افتراضية للوظائف الأهلية (قطاع خاص)
    if 'الاهلية' in title or 'أهلية' in title or 'شركة' in title:
        return 'https://cdn-icons-png.flaticon.com/512/2830/2830305.png' # أيقونة شركة
    
    # صورة افتراضية للوظائف الحكومية العامة
    return 'https://cdn-icons-png.flaticon.com/512/8291/8291079.png' # أيقونة حكومة

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
            pub_date = "اليوم"
            
        category = entry.category if 'category' in entry else "الكل"
        
        # تنظيف المحتوى واستخراج اللوجو الذكي
        raw_description = entry.description
        clean_description = clean_html_content(raw_description)
        logo_url = get_logo_for_title(title)
        
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
    from telegram_scraper import fetch_telegram_jobs
    
    # أولاً جلب وظائف الموقع (RSS)
    rss_jobs = fetch_and_parse_jobs()
    
    # ثانياً جلب وظائف التليجرام مع تمرير الوظائف الحالية لتجنب التكرار
    telegram_jobs = fetch_telegram_jobs(existing_jobs=rss_jobs)
    
    # دمج الوظائف
    all_jobs = rss_jobs + telegram_jobs
    
    # حفظ الملف كـ JSON
    output_file = 'jobs.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=4)
        
    print(f"تم بنجاح جلب وتنظيف {len(rss_jobs)} من الموقع و {len(telegram_jobs)} من التليجرام.")
    print(f"العدد الكلي للوظائف المحفوظة في {output_file} هو: {len(all_jobs)}")

if __name__ == "__main__":
    main()
