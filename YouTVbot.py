
import telebot
import yt_dlp
import requests
import re
import os

bot = telebot.TeleBot("5813563221:AAHZIjn4wfYNq_6M-uOJAPGpHKzERNohVzA")
bot.timeout = 3600

YOUTUBE_LINK_REGEX = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'

# This dictionary will store the video URLs and other necessary information
video_info = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hi! Send me a YouTube video link and I'll download it for you.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    try:
        print(f"Received message: {message.text}")
        match = re.search(YOUTUBE_LINK_REGEX, message.text)
        if not match:
            print("No match found")
            bot.reply_to(message, "Sorry, that doesn't seem to be a valid YouTube link.")
            return

        print(f"Match found: {match.group()}")
        with yt_dlp.YoutubeDL() as ydl:
            info_dict = ydl.extract_info(match.group(), download=False)
            video_title = info_dict.get('title', None)
            formats = info_dict.get('formats', None)

        # Store the video URL and other necessary information in the dictionary
        video_info[message.chat.id] = {
            'url': match.group(),
            'title': video_title,
            'formats': formats,
            'ext': info_dict['ext']  # Store the extension
        }

        # Send available resolutions to user
        resolutions = []
        for f in formats:
            if f.get('format_note') and f.get('ext') == 'mp4' and f.get('acodec') != 'none':
                if 'filesize' in f and f['filesize'] is not None:
                    resolutions.append(f"{f['format_note']} ({f['filesize'] / 1024 / 1024:.2f} MB)")
                else:
                    resolutions.append(f"{f['format_note']} (Unknown Size)")
        resolutions = list(set(resolutions))
        resolutions.sort(key=lambda r: int(r[:-1]) if r[:-1].isdigit() else 0)

        # Create inline keyboard
        keyboard = telebot.types.InlineKeyboardMarkup()
        for r in resolutions:
            if r.split(' ')[0] != 'Default':  # Exclude the 'Default' option
                button = telebot.types.InlineKeyboardButton(text=r, callback_data=r)
                keyboard.add(button)

        bot.send_message(message.chat.id, f"Available resolutions for '{video_title}':",                reply_markup=keyboard)
    except yt_dlp.utils.DownloadError as e:
        print(e)
        bot.reply_to(message, "Sorry, I couldn't download that video.")
    except requests.exceptions.RequestException as e:
        print(e)
        bot.reply_to(message, "Sorry, there was a network issue.")
    except Exception as e:
        print(e)
        bot.reply_to(message, "Sorry, I couldn't download that video.")

def clean_filename(filename):
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c==' ']).rstrip()



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    resolution = call.data.split(' ')[0]  # This will be the resolution selected by the user

    # Retrieve the video URL and other necessary information from the dictionary
    info = video_info[call.message.chat.id]

    # Now you can download the video with the selected resolution
    filename = clean_filename(info['title']) + '_' + resolution + '.' + info['ext']
    if not os.path.isfile(filename):
        ydl_opts = {
            'format': 'bestvideo[height<='+resolution+']+bestaudio/best[height<='+resolution+']',
            'outtmpl': filename,  # Use the cleaned video title as the filename
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([info['url']])

    bot.send_message(call.message.chat.id, "Video downloaded successfully.\nNow uploading...\nPlease wait....")
    bot.send_video(call.message.chat.id, open(filename, 'rb'), caption=info['title'], timeout=5000)

    # Remove the inline keyboard
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

bot.polling()