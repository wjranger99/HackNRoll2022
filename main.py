from pymongo import aggregation
from telebot.apihelper import send_message
from telebot import apihelper

from telebot.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from db import db, BOT_TOKEN
import datetime
import telebot

bot = telebot.TeleBot(BOT_TOKEN)
bot.set_my_commands([
    BotCommand("start", "Start up the bot"),
    BotCommand("update_gpa", "Update your GPA here!")
])

user_dict = {}

# ========================== Section 1 of the Code =============================== #

# handle_start(message)
# param[in] message: The message sent by the user.
# 
# Function: Used to set up the user. We require the user to set up
# the Telegram Bot inside first before the user sets up his / her 
# account. Used to handle the /start command.
#
# If the chat type is private, check whether a group has been 
# registered. If there are no groups, request user to start the 
# bot in a group. If register, we would ask the user which group
# he would like to be in.


@bot.message_handler(commands=["start"])
def handle_start(message):
    
    chat_id = message.chat.id
    start_message = ""
    

    if message.chat.type != "private":
        if db.project.find_one({"group_id": chat_id}) == None:
            db.project.insert_one({
                "group_id": chat_id,
                "group_name": message.chat.title
            })
        start_message += "The bot had been set up for the group. Please set it up from the user side."
        bot.send_message(chat_id, start_message)
        return

    else:
        if len(list(db.project.find())) == 0:
            start_message += "No groups found. Please add the bot into a group of your choice and start it."
            bot.send_message(chat_id, start_message)
            return

        else:
            buttons = []
            for key in list(db.project.find()):
                row = []
                button = InlineKeyboardButton(key["group_name"], callback_data=f'Chosen Group {key["group_name"]}')
                row.append(button)
                buttons.append(row)
            start_message += "Select a group that you will be like to post in."
            bot.send_message(chat_id, start_message, reply_markup=InlineKeyboardMarkup(buttons))


# retrieve_user_info(chat_id)
# param[in] chat_id: The id of the private chat with the bot.
# 
# Function: This is the starting point of the register_next_step_handler.

def retrieve_user_info(chat_id):
    user_dict["date"] = datetime.datetime.now().strftime("%x")
    msg = bot.send_message(chat_id, "Hi! How do we address you?")
    bot.register_next_step_handler(msg, process_name_step)


# process_name_step(message)
# param[in] message: The message that was inputted by the user.
# 
# Function: Saves the name of the user in the user_dict and 
# proceeds with the next step. If an error is thrown, repeat 
# the whole process again.

def process_name_step(message):
    try:
        name = message.text
        user_dict["name"] = name
        msg = bot.send_message(message.chat.id, "Write down your target GPA")
        bot.register_next_step_handler(msg, process_gpa_step)

    except Exception:
        msg = bot.reply_to(message, "Please introduce yourself again")
        bot.register_next_step_handler(msg, process_name_step)

# process_gpa_step(message)
# param[in] message: The message that was inputted by the user.
#
# Function: Saves the target gpa of the user in the user_dict 
# and proceeds with the next step. If an error is thrown, repeat 
# the whole process again.

def process_gpa_step(message):
    try:
        gpa = float(message.text)
        
        if gpa < 0 or gpa > 4.0:
            msg = bot.reply_to(message, "Please input a valid target GPA.")
            bot.register_next_step_handler(msg, process_gpa_step)
            return

        user_dict["targetgpa"] = gpa
        msg = bot.send_message(message.chat.id, "What secrets would you like to share?")
        bot.register_next_step_handler(msg, process_kink_step)

    except Exception:
        msg = bot.reply_to(message, "Please re-enter your GPA! Do note that the GPA must be a number between 0 to 4.")
        bot.register_next_step_handler(msg, process_gpa_step)
        
# process_kink_step(message)
# param[in] message: The text that the user had inputted.
#
# Function: 
# 1. Stores the kink in the user dictionary.
# 2. CREATE a document in the database with the user_dict.
# 3. Delete the group information in the "project" collection. 
# If another user would like to start the whole thing again in
# the same group, he would have to start the bot again in the
# group.

def process_kink_step(message):
    try:
        kink = message.text
        user_dict["kink"] = kink
        db.covid.insert_one(user_dict)
        group_id = user_dict["group_id"]
        db.project.find_one_and_delete({"group_id": group_id})

        bot.send_message(message.chat.id, "Information saved successfully! Thanks for filling up the information")

    except Exception as e:
        print(e)
        msg = bot.reply_to(message, "We had encountered an error in saving your secret. Please tell us your secret again.")
        bot.register_next_step_handler(msg, process_kink_step)
        
# handle_callback(call)
# Function: This function is used to handle callbacks
# if there are any.
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    
    chat_id = call.message.chat.id
    print(chat_id)
    user = call.message.chat.first_name
    data = call.data
    splitted = data.split()
    print(splitted)
    intent = data.split()[0]
    grp_name = ' '.join(splitted[2:])

    if intent == "Chosen":
        print(grp_name)
        
        # group_name = data.split()[0:][2]
        send_message_logic(chat_id, grp_name)
        return

    return

# send_message_logic(chat_id, group_name)
# param[in] chat_id : The id of the private chat with the bot
# param[in] group_name: The name of the group that the user has selected
# 
# Step 1: Search for the Group ID in the "project" collection with the group name.
# Step 2: Save the group_id and group_name in the user_dict
# Step 3: Runs the retrieve_user_info
def send_message_logic(chat_id, group_name):    
    bot.send_message(chat_id, f'You have chosen the group {group_name} to post the images.')
    group_id = db.project.find_one({"group_name": group_name})["group_id"]
    print(group_id)
    user_dict["group_name"] = group_name
    user_dict["group_id"] = group_id
    user_dict["private_chat_id"] = chat_id
    retrieve_user_info(chat_id)
    return

# ========================== Section 2 of the Code =============================== #

# handle_update(message)
# param[in] message: The text input by the user
#
# Function: Used to handle the "/update" command

@bot.message_handler(commands=["update_gpa"])
def handle_update(message):
    chat_id = message.chat.id
    print(message.chat.id)

    if message.chat.type == "private":
      bot.send_message(chat_id, "This function only works for private chat with the bot.")
      return

    if db.covid.find_one({"private_chat_id": chat_id}) == None:
        bot.send_message(chat_id, "Please press /start to begin the bot.")
        return

    message = bot.send_message(chat_id, "Well done for completing this Semester. Now the time has come. What is your GPA")
    bot.register_next_step_handler(message, process_receive_gpa)
    
# process_receive_gpa(message)
# param[in] message: The text input by the user.
#
# Function: Logic catered to processing the GPA

def process_receive_gpa(message):
    try:
        new_gpa = float(message.text)

        if new_gpa < 0 or new_gpa > 4:
            msg = "Please enter a valid GPA."
            bot.register_next_step_handler(msg, process_receive_gpa)
            return

        chat_id = message.chat.id
        old_gpa = db.covid.find_one({"private_chat_id": chat_id})["targetgpa"]
            
        if old_gpa > new_gpa:
            kink = db.covid.find_one({"private_chat_id": chat_id})["kink"]
            group_id = db.covid.find_one({"private_chat_id": chat_id})["group_id"]
            name = db.covid.find_one({"private_chat_id": chat_id})["name"]
            confession = f'{name} has failed to achieve his GPA and he has a confession to make. \n\n\n\n {kink}'
            bot.send_message(group_id, confession)
            bot.send_message(chat_id, "As agreed, we will be sending your confession onto the page.")

        else:
            bot.send_message(chat_id, "Congrats on achieving your goal! I am so proud of you.")

        db.covid.find_one_and_delete({"private_chat_id": chat_id})

    except Exception:
        bot.send_message(message.chat.id, "There was an error with processing your command.")


bot.infinity_polling()
