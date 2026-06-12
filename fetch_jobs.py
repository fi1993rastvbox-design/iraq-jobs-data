import feedparser
import json
import re
from bs4 import BeautifulSoup
import uuid
from datetime import datetime
from duckduckgo_search import DDGS
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
    'مكافحة الارهاب': 'https://upload.wikimedia.org/wikipedia/ar/thumb/0/0c/Iraqi_Counter_Terrorism_Service_logo.png/400px-Iraqi_Counter_Terrorism_Service_logo.png'
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
    try:
        # استخراج أول 4 كلمات من العنوان للبحث عنها
        words = title.split()
        short_title = ' '.join(words[:4]) if len(words) >= 4 else title
        search_query = f"شعار {short_title} العراق"
        
        with DDGS() as ddgs:
            results = [r for r in ddgs.images(search_query, max_results=1)]
            if results and 'image' in results[0]:
                time.sleep(1) # لتفادي الحظر
                return results[0]['image']
    except Exception as e:
        print(f"فشل جلب الصورة لـ {title}: {e}")
    
    # صورة افتراضية للوظائف الأهلية (قطاع خاص)
    if 'الاهلية' in title or 'أهلية' in title or 'شركة' in title:
        return 'https://cdn-icons-png.flaticon.com/512/2830/2830305.png' # أيقونة شركة
    
    # صورة افتراضية للوظائف الحكومية غير المعرفة بالقاموس
    return 'https://cdn-icons-png.flaticon.com/512/8291/8291079.png' # أيقونة حكومة

def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # استخراج النص الصافي
    text = soup.get_text(separator="\n").strip()
    
    # تنظيف الروابط والكلمات الإعلانية باستخدام regex
    for spam in SPAM_PHRASES:
        text = re.sub(rf"{spam}.*", "", text, flags=re.IGNORECASE)
        text = text.replace(spam, "")
        
    # إزالة الأسطر الفارغة الزائدة
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # دمج الأسطر مع فواصل للحفاظ على الترتيب
    cleaned_text = "\n".join(lines)
    return cleaned_text

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
    jobs = fetch_and_parse_jobs()
    
    # حفظ الملف كـ JSON
    output_file = 'jobs.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=4)
        
    print(f"تم بنجاح جلب وتنظيف {len(jobs)} وظيفة وحفظها في {output_file}")

if __name__ == "__main__":
    main()
