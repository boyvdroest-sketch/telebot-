import os
import time
from flask import Flask, request
import telebot
from telebot import types

# Get bot token from environment variable
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Add your admin user ID here
ADMIN_ID = 5408261209  # Replace with your actual Telegram user ID

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Store group info and user lists
target_groups = {}  # Format: {group_id: group_info}
user_lists = {}     # Format: {list_name: [usernames]}

@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This bot is for admin use only.")
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📋 Manage User Lists", callback_data="manage_lists"),
        types.InlineKeyboardButton("👥 Set Target Group", callback_data="set_group"),
        types.InlineKeyboardButton("🚀 Start Adding", callback_data="start_adding"),
        types.InlineKeyboardButton("📊 Status", callback_data="status")
    )
    
    bot.send_message(
        message.chat.id,
        "🤖 **Group Member Adder Bot**\n\n"
        "Use this bot to add members to Telegram groups by username.\n\n"
        "**Features:**\n"
        "• Create and manage user lists\n"
        "• Set target group\n"
        "• Add members automatically\n"
        "• Anti-ban protection with delays",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "manage_lists")
def manage_lists_handler(call):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📝 Create New List", callback_data="create_list"),
        types.InlineKeyboardButton("📤 Import Users", callback_data="import_users"),
        types.InlineKeyboardButton("👀 View Lists", callback_data="view_lists"),
        types.InlineKeyboardButton("🗑️ Delete List", callback_data="delete_list"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_main")
    )
    
    bot.edit_message_text(
        "📋 **Manage User Lists**\n\n"
        "Choose an option to manage your user lists:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "create_list")
def create_list_handler(call):
    msg = bot.send_message(
        call.message.chat.id,
        "📝 **Create New User List**\n\n"
        "Please send me the list name:"
    )
    bot.register_next_step_handler(msg, process_list_name)

def process_list_name(message):
    list_name = message.text.strip()
    if list_name in user_lists:
        bot.send_message(message.chat.id, f"❌ List '{list_name}' already exists!")
        return
    
    user_lists[list_name] = []
    msg = bot.send_message(
        message.chat.id,
        f"✅ List '{list_name}' created!\n\n"
        "Now send me usernames (one per line, with @):\n"
        "Example:\n"
        "@username1\n"
        "@username2\n"
        "@username3"
    )
    bot.register_next_step_handler(msg, process_usernames, list_name)

def process_usernames(message, list_name):
    usernames = message.text.strip().split('\n')
    valid_usernames = []
    
    for username in usernames:
        username = username.strip()
        if username.startswith('@') and len(username) > 1:
            valid_usernames.append(username)
    
    user_lists[list_name] = valid_usernames
    
    bot.send_message(
        message.chat.id,
        f"✅ Added {len(valid_usernames)} users to list '{list_name}'!\n\n"
        f"**Usernames:**\n" + "\n".join(valid_usernames[:10]) + 
        ("\n..." if len(valid_usernames) > 10 else "")
    )

@bot.callback_query_handler(func=lambda call: call.data == "set_group")
def set_group_handler(call):
    msg = bot.send_message(
        call.message.chat.id,
        "👥 **Set Target Group**\n\n"
        "To set the target group:\n"
        "1. Add this bot to the group as admin\n"
        "2. Make sure the bot has permission to add members\n"
        "3. Send me the group username (e.g., @groupname) or forward a message from the group"
    )
    bot.register_next_step_handler(msg, process_group_info)

def process_group_info(message):
    try:
        if message.forward_from_chat:
            # Message was forwarded from a group
            group = message.forward_from_chat
            target_groups[ADMIN_ID] = {
                'id': group.id,
                'username': group.username,
                'title': group.title
            }
        elif message.text.startswith('@'):
            # Group username provided
            group_username = message.text
            group = bot.get_chat(group_username)
            target_groups[ADMIN_ID] = {
                'id': group.id,
                'username': group.username,
                'title': group.title
            }
        else:
            bot.send_message(message.chat.id, "❌ Please provide a valid group username or forward a message from the group.")
            return
        
        bot.send_message(
            message.chat.id,
            f"✅ Target group set!\n\n"
            f"**Group:** {target_groups[ADMIN_ID]['title']}\n"
            f"**Username:** @{target_groups[ADMIN_ID].get('username', 'N/A')}\n"
            f"**ID:** {target_groups[ADMIN_ID]['id']}"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error setting group: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "start_adding")
def start_adding_handler(call):
    if ADMIN_ID not in target_groups:
        bot.send_message(call.message.chat.id, "❌ Please set a target group first!")
        return
    
    if not user_lists:
        bot.send_message(call.message.chat.id, "❌ Please create a user list first!")
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for list_name in user_lists.keys():
        keyboard.add(types.InlineKeyboardButton(f"📋 {list_name}", callback_data=f"add_from_{list_name}"))
    keyboard.add(types.InlineKeyboardButton("🔙 Back", callback_data="manage_lists"))
    
    bot.edit_message_text(
        "🚀 **Start Adding Members**\n\n"
        "Choose which list to add from:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_from_'))
def add_from_list_handler(call):
    list_name = call.data.replace('add_from_', '')
    usernames = user_lists.get(list_name, [])
    
    if not usernames:
        bot.answer_callback_query(call.id, "❌ This list is empty!")
        return
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Start Adding", callback_data=f"confirm_add_{list_name}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="start_adding")
    )
    
    group_info = target_groups[ADMIN_ID]
    bot.edit_message_text(
        f"🚀 **Ready to Add Members**\n\n"
        f"**Target Group:** {group_info['title']}\n"
        f"**User List:** {list_name}\n"
        f"**Users to Add:** {len(usernames)}\n\n"
        f"⚠️ **Important:**\n"
        f"• Bot must be admin in the group\n"
        f"• Bot needs 'Add Members' permission\n"
        f"• Adding too fast may trigger limits\n"
        f"• Some users may have privacy restrictions",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_add_'))
def confirm_add_handler(call):
    list_name = call.data.replace('confirm_add_', '')
    usernames = user_lists.get(list_name, [])
    group_info = target_groups[ADMIN_ID]
    
    bot.edit_message_text(
        f"⏳ **Adding Members...**\n\n"
        f"Starting to add {len(usernames)} users to {group_info['title']}\n"
        f"This may take a while...",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Start the adding process
    add_members_to_group(call.message, group_info['id'], usernames, list_name)

def add_members_to_group(message, group_id, usernames, list_name):
    success_count = 0
    fail_count = 0
    failed_users = []
    
    status_msg = bot.send_message(
        message.chat.id,
        f"🔄 **Adding Members Progress**\n\n"
        f"✅ Successful: 0\n"
        f"❌ Failed: 0\n"
        f"📊 Total: {len(usernames)}\n"
        f"⏰ Processing..."
    )
    
    for i, username in enumerate(usernames):
        try:
            # Remove @ if present
            clean_username = username.lstrip('@')
            
            # Try to add user to group
            bot.add_chat_member(group_id, clean_username)
            success_count += 1
            
            # Update progress every 5 users or on last user
            if (i + 1) % 5 == 0 or (i + 1) == len(usernames):
                bot.edit_message_text(
                    f"🔄 **Adding Members Progress**\n\n"
                    f"✅ Successful: {success_count}\n"
                    f"❌ Failed: {fail_count}\n"
                    f"📊 Total: {len(usernames)}\n"
                    f"⏰ Processing... ({i+1}/{len(usernames)})",
                    message.chat.id,
                    status_msg.message_id
                )
            
            # Anti-ban delay: wait 3-8 seconds between adds
            delay = 5  # seconds
            time.sleep(delay)
            
        except Exception as e:
            fail_count += 1
            failed_users.append(f"{username} - {str(e)}")
            print(f"Failed to add {username}: {e}")
    
    # Final status
    result_text = (
        f"✅ **Adding Complete!**\n\n"
        f"**Results for {list_name}:**\n"
        f"✅ Successful: {success_count}\n"
        f"❌ Failed: {fail_count}\n"
        f"📊 Total Processed: {len(usernames)}\n"
        f"🎯 Success Rate: {(success_count/len(usernames)*100):.1f}%"
    )
    
    if failed_users:
        result_text += f"\n\n**Failed Users:**\n" + "\n".join(failed_users[:10])
        if len(failed_users) > 10:
            result_text += f"\n... and {len(failed_users) - 10} more"
    
    bot.edit_message_text(
        result_text,
        message.chat.id,
        status_msg.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == "status")
def status_handler(call):
    group_info = target_groups.get(ADMIN_ID, {})
    list_count = len(user_lists)
    total_users = sum(len(users) for users in user_lists.values())
    
    status_text = (
        "📊 **Bot Status**\n\n"
        f"**Target Group:** {group_info.get('title', 'Not set')}\n"
        f"**User Lists:** {list_count}\n"
        f"**Total Users:** {total_users}\n\n"
    )
    
    if user_lists:
        status_text += "**Available Lists:**\n"
        for list_name, users in user_lists.items():
            status_text += f"• {list_name}: {len(users)} users\n"
    
    bot.edit_message_text(
        status_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Back", callback_data="back_main")
        )
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main_handler(call):
    start_command(call.message)

@app.route('/')
def home():
    return "Group Member Adder Bot is running!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_data().decode("utf-8")
    update_obj = telebot.types.Update.de_json(update)
    bot.process_new_updates([update_obj])
    return "OK", 200

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("⚠️ TELEGRAM_BOT_TOKEN environment variable is required")
    
    # Set webhook
    try:
        bot.remove_webhook()
        replit_domain = os.environ.get("REPLIT_DEV_DOMAIN")
        render_domain = os.environ.get("RENDER_EXTERNAL_URL")
        
        if replit_domain:
            webhook_url = f"https://{replit_domain}/{TOKEN}"
        elif render_domain:
            webhook_url = f"{render_domain}/{TOKEN}"
        else:
            webhook_url = None
            
        if webhook_url:
            bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook set to: {webhook_url}")
        else:
            print("⚠️ No domain found for webhook")
            
    except Exception as e:
        print(f"⚠️ Webhook setup error: {e}")
    
    print("🚀 Group Member Adder Bot is running!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
