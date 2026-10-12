# Discord Bot (Modular & Slash Commands)

บอท Discord พัฒนาด้วย Python และ `discord.py` สถาปัตยกรรม Cogs พร้อมรองรับทั้ง **Slash Commands (`/`)** และ **Prefix Commands (`.`)** มีระบบเล่นเพลง YouTube, สถิติเซิร์ฟเวอร์แบบ Real-time (ป้องกัน Rate Limit) และระบบ Voice Channel Logging

---

## 🌟 โครงสร้างโปรเจกต์ใหม่ (Modular Architecture)

```
DiscordBot/
├── .env                  # การตั้งค่า Token
├── requirements.txt      # รายการ Dependencies
├── bot.py                # จุดเริ่มต้นของบอท (Main Runner & Sync Commands)
└── cogs/                 # โมดูลแยกตามการใช้งาน
    ├── general.py        # คำสั่งทั่วไป (/hello, /ping, /info, /bothelp)
    ├── music.py          # ระบบเพลง YouTube, คิว, Bass Boost (/play, /skip, etc.)
    ├── stats.py          # สถิติเซิร์ฟเวอร์ (อัปเดตอัตโนมัติทุก 10 นาที ป้องกัน Rate Limit)
    └── voice_logs.py     # บันทึกการเข้า/ออกห้องเสียง สลับห้อง เปิด/ปิดไมค์
```

---

## 🚀 ฟีเจอร์หลัก (Features)

### 🎵 1. Music Player
- สตรีมเพลงจาก YouTube ผ่าน URL หรือค้นหาจากชื่อเพลง
- ระบบจัดการคิวเพลง (Queue, Skip, Clear, Pause, Resume, Stop)
- ปรับแต่งเสียง **Bass Boost** (`/bassboost`, `/bass [1-10]`)
- คำสั่งตัดการเชื่อมต่อและเคลียร์สถานะเมื่อค้าง (`/leave`, `/forceleave`)

### 📊 2. Server Statistics (Rate Limit Safe)
- สถิติแบบละเอียด: จำนวนสมาชิกทั้งหมด, ผู้ใช้จริง (Humans), บอท (Bots), คนในห้องเสียง
- สร้างหมวดหมู่ `📊 Server Statistics` และช่องเสียงแสดงสถิติอัตโนมัติ
- **ระบบป้องกัน Rate Limit:** รัน Background Task อัปเดตทุก 10 นาที และตรวจสอบก่อนว่าตัวเลขเปลี่ยนจริงหรือไม่ จึงจะยิง API แก้ไขชื่อห้อง

### 📝 3. Voice Channel Logging
- บันทึกการเข้า/ออกห้องเสียง, การย้ายห้อง, และการเปิด/ปิดไมค์แบบ Real-time
- ส่งการแจ้งเตือนลงช่อง `คนเข้าออก` ในหมวด `in-out` (หรือช่อง `bot-logs` / `logs`) ด้วย Discord Embed สวยงาม

---

## 🛠️ ขั้นตอนการติดตั้งและการเปิดใช้งาน

### 1. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```
*(หากใช้ Python 3.13 ขึ้นไป ตัวโปรเจกต์รวม `audioop-lts` ไว้ใน requirements เรียบร้อยแล้ว)*

### 2. ติดตั้ง FFmpeg
- ดาวน์โหลด FFmpeg จาก [ffmpeg.org](https://ffmpeg.org/download.html)
- แตกไฟล์และเพิ่มโฟลเดอร์ `bin` เข้าในระบบ **System Environment Variables (PATH)**
- ตรวจสอบโดยรัน `ffmpeg -version` ใน Command Prompt / PowerShell

### 3. ตั้งค่า Token ใน `.env`
เปิดไฟล์ `.env` แล้วระบุ Discord Bot Token:
```env
DISCORD_TOKEN=your_actual_bot_token_here
```

### 4. รันบอท
```bash
python bot.py
# หรือ
py bot.py
```
*(เมื่อบอทรันขึ้นมา จะทำการโหลด Cogs ทั้งหมดและ Sync Slash Commands ให้เซิร์ฟเวอร์โดยอัตโนมัติ)*

---

## 📜 รายการคำสั่งทั้งหมด (Commands List)

รองรับทั้ง **Slash Commands (`/`)** และ **Prefix Commands (`.`)**:

### 🎵 เพลง (Music)
| Slash Command | Prefix Command | คำอธิบาย |
| :--- | :--- | :--- |
| `/play <query>` | `.play <query>` | เล่นเพลงจาก YouTube ด้วยชื่อหรือ URL |
| `/pause` | `.pause` | หยุดเพลงชั่วคราว |
| `/resume` | `.resume` | เล่นเพลงต่อ |
| `/skip` | `.skip` | ข้ามเพลงปัจจุบัน |
| `/stop` | `.stop` | หยุดเล่นเพลงและเคลียร์คิว |
| `/queue` | `.queue` | ดูรายการเพลงในคิว |
| `/clear` | `.clear` | ล้างเพลงทั้งหมดในคิว |
| `/bassboost` | `.bassboost` | เปิด/ปิด โหมด Bass Boost |
| `/bass <1-10>` | `.bass <1-10>` | ตั้งค่าระดับความแรง Bass Boost |
| `/leave` | `.leave` | ให้ออกจากห้องเสียง |
| `/forceleave` | `.forceleave` | บังคับตัดการเชื่อมต่อกรณีบอทค้าง |

### 📊 สถิติเซิร์ฟเวอร์ (Stats)
| Slash Command | Prefix Command | คำอธิบาย |
| :--- | :--- | :--- |
| `/setupstats` | `.setupstats` | สร้างหมวดและช่องแสดงสถิติเซิร์ฟเวอร์ |
| `/stats` | `.stats` | ดูการ์ดสถิติเซิร์ฟเวอร์แบบละเอียด |
| `/debug` | `.debug` | ตรวจสอบจำนวนสมาชิกเชิงลึก |

### 📝 คำสั่งทั่วไปและระบบ Log (General & Logs)
| Slash Command | Prefix Command | คำอธิบาย |
| :--- | :--- | :--- |
| `/bothelp` | `.bothelp` | แสดงคู่มือคำสั่งทั้งหมด |
| `/ping` | `.ping` | วัดค่าความหน่วงของบอท (Latency) |
| `/hello` | `.hello` | ทักทายบอท |
| `/info` | `.info` | ดูข้อมูลเบื้องต้นของเซิร์ฟเวอร์ |
| `/testlog` | `.testlog` | ทดสอบการส่งข้อความเข้าห้องบันทึกเสียง |
