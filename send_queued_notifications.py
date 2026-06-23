import json
import os
import time
import firebase_admin
from firebase_admin import credentials, messaging

# مسار ملف الـ Queue الخاص بالإشعارات
QUEUE_FILE_PATH = 'notifications_queue.json'

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate('../assets/service-account.json')
        firebase_admin.initialize_app(cred)

def process_queue():
    if not os.path.exists(QUEUE_FILE_PATH):
        print("لا يوجد ملف طابور إشعارات.")
        return

    with open(QUEUE_FILE_PATH, 'r', encoding='utf-8') as f:
        try:
            queue = json.load(f)
        except json.JSONDecodeError:
            print("ملف الطابور فارغ أو تالف.")
            return

    if not queue:
        print("لا توجد إشعارات جديدة في الطابور.")
        return

    print(f"تم العثور على {len(queue)} إشعار(ات) في الطابور. جاري الانتظار لمدة 5 دقائق لضمان تحديث الكاش...")
    # الانتظار 5 دقائق لكي يتحدث كاش GitHub وتظهر الوظيفة للمستخدمين عند ضغطهم على الإشعار
    time.sleep(300)

    init_firebase()
    
    topic_map = {
      'بغداد': 'baghdad', 'البصرة': 'basra', 'نينوى': 'nineveh', 'أربيل': 'erbil',
      'النجف': 'najaf', 'ذي قار': 'dhi_qar', 'كركوك': 'kirkuk', 'الأنبار': 'anbar',
      'ديالى': 'diyala', 'المثنى': 'muthanna', 'الديوانية': 'diwaniya', 'ميسان': 'maysan',
      'واسط': 'wasit', 'صلاح الدين': 'saladin', 'دهوك': 'duhok', 'السليمانية': 'sulaymaniyah',
      'بابل': 'babil', 'كربلاء': 'karbala',
      'القطاع الحكومي العام': 'gov_sector', 'القطاع الخاص': 'private_sector'
    }

    for job in queue:
        print(f"جاري معالجة إشعار الوظيفة: {job.get('title')}")
        # JobModel Dart class properties matching
        # in dart it's: category (sector), location (if we extracted it, but usually the location is in the title string)
        # Actually in add_job_screen.dart: location is extracted from title, but only saved to category!
        # wait! JobModel doesn't have a 'location' field. In `github_admin_service.dart`, `job.location` was used but wait, let me check `job_model.dart`.
        # I'll just try to get province from the title if not in dict.
        
        title = job.get('title', '')
        sector = job.get('category', '')
        
        # استخراج المحافظة من العنوان (عادة تكون بين أقواس)
        province = ''
        if '(' in title and ')' in title:
            province = title.split('(')[1].split(')')[0].strip()

        p_topic = topic_map.get(province)
        s_topic = topic_map.get(sector)
        
        # تكوين الشرط: نرسل دائماً لـ all_users، وإذا توفرت المحافظة/القطاع نرسل للمشتركين بها
        conditions = ["'all_users' in topics"]
        if p_topic:
            conditions.append(f"'topic_{p_topic}' in topics")
        if s_topic:
            conditions.append(f"'topic_{s_topic}' in topics")
            
        condition_str = " || ".join(conditions)
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"وظيفة جديدة في {province if province else 'العراق'}",
                    body=title
                ),
                data={'type': 'job'},
                condition=condition_str,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='custom_tone',
                        channel_id='iraq_jobs_alerts_channel'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound='default', content_available=True)
                    )
                )
            )
            response = messaging.send(message)
            print(f"تم إرسال الإشعار بنجاح: {response}")
        except Exception as e:
            print(f"فشل في إرسال الإشعار: {e}")
            
    # تفريغ الطابور بعد الانتهاء
    with open(QUEUE_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump([], f)
    print("تم تفريغ الطابور.")

if __name__ == "__main__":
    process_queue()
