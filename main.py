# Importing the required modules
from telebot.apihelper import send_message
from telebot import apihelper
from telebot.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from db import db, BOT_TOKEN
import telebot

bot = telebot.TeleBot(BOT_TOKEN)
bot.set_my_commands([
    BotCommand("start", "Start up the bot"),
    BotCommand("update_gpa", "Update your GPA here!")
])

user_dict = {}
chosen_chat = None
given_time = None
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
# Stores the date into the database.

def retrieve_user_info(chat_id):
  degenerate = InlineKeyboardButton("Degenerate", callback_data="Prefer degenerate")
  praise = InlineKeyboardButton("Praise", callback_data="Prefer praise")
  buttons = [[degenerate], [praise]]
  bot.send_message(chat_id, '''Hi! My name is Joi, and I’m your guide to a better GPA. Before we continue, I want to know more about you. Like, what’s your motivation style?''', reply_markup=InlineKeyboardMarkup(buttons))
    

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
        if user_dict["preference"] == "praise":
          msg = bot.send_message(message.chat.id, "It’s really nice to meet you. What’s your target GPA anyways?")

        elif user_dict["preference"] == "degenerate":
          msg = bot.send_message(message.chat.id, "Anyway, what’s the GPA you want to get?")
        
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
        if user_dict["preference"] == "praise":
          msg = bot.send_message(message.chat.id, "I believe in you! Could you send me an embarrassing image of yourself? If you don’t manage to reach your goals, I’ll send it to all your friends so you’ll stay motivated to study!")

        elif user_dict["preference"] == "degenerate":
          msg = bot.send_message(message.chat.id, "Also, I need you to send me an image of yourself. Something private, that you don’t want other people to see.")

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
        # kink = message.text
        kink = message.photo[0].file_id
        # user_dict["kink"] = kink
        # user_dict["kink"] = bot.get_file_url(kink)
        user_dict["kink"] = kink
        db.covid.insert_one(user_dict)
        group_id = user_dict["group_id"]
        db.project.find_one_and_delete({"group_id": group_id})

        bot.send_message(message.chat.id, "Information saved successfully! Thanks for filling up the information")

    except Exception:
        msg = bot.reply_to(message, "We had encountered an error in saving your secret. Please tell us your secret again.")
        bot.register_next_step_handler(msg, process_kink_step)
        
# handle_callback(call)
# Function: This function is used to handle callbacks
# if there are any.
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    
    chat_id = call.message.chat.id
    data = call.data
    splitted = data.split()
    intent = data.split()[0]
    grp_name = ' '.join(splitted[2:])

    if intent == "Chosen":
        send_message_logic(chat_id, grp_name)
        retrieve_user_info(chat_id)
        return

    elif intent == "Prefer":
        option = data.split()[1]
        user_dict["preference"] = option
        chat_message = ""

        if option == "praise":
          chat_message += "That’s good! I feel much more comfortable talking to you now that I know you’re a positive person, just like me! What’s your name, by the way?"

        elif option == "degenerate":
          chat_message += "I mean, I don’t really know you so thanks for sharing I guess. What’s your name, by the way?"
    
        msg = bot.send_message(chat_id, chat_message)
        bot.register_next_step_handler(msg, process_name_step)
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
    user_dict["group_name"] = group_name
    user_dict["group_id"] = group_id
    user_dict["private_chat_id"] = chat_id
    return

# ========================== Section 2 of the Code =============================== #

# handle_update(message)
# param[in] message: The text input by the user
#
# Function: Used to handle the "/update" command

@bot.message_handler(commands=["update_gpa"])
def handle_update(message):
    chat_id = message.chat.id

    if message.chat.type != "private":
      bot.send_message(chat_id, "This function only works for private chat with the bot.")
      return

    if db.covid.find_one({"private_chat_id": chat_id}) == None:
        bot.send_message(chat_id, "Please press /start to begin the bot.")
        return

    response = ""
    if db.covid.find_one({"private_chat_id": chat_id})["preference"] == "praise":
      response += "Hi! I heard you got your GPA back?"

    elif db.covid.find_one({"private_chat_id": chat_id})["preference"] == "degenerate":
      response += "Hello my sweet boy. What’s your GPA?"


    msg = bot.send_message(chat_id, response)
    bot.register_next_step_handler(msg, process_receive_gpa)
    
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
        print("old",old_gpa)
        print("new",new_gpa)
        if old_gpa > new_gpa:
            
            kink = db.covid.find_one({"private_chat_id": chat_id})["kink"]
            print(kink)
            group_id = db.covid.find_one({"private_chat_id": chat_id})["group_id"]
            name = db.covid.find_one({"private_chat_id": chat_id})["name"]
            confession = ""
            if db.covid.find_one({"private_chat_id": chat_id})["preference"] == "praise":
              confession += f"Hi guys, {name} added me here a few months ago to motivate him to do well.Unfortunately, his GPA just fell short of his target one, and so he asked me to post this as a punishment:"
              # photo = open(kink, 'rb')
              
            # if db.covid.find_one({"private_chat_id": chat_id})["preference"] == "praise":
            #   confession += 'Good news everyone! name has achieved his goal of getting a GPA better than target goal! I’ll be seeing myself out now, bye~

            elif db.covid.find_one({"private_chat_id": chat_id})["preference"] == "degenerate":
              confession += f'Hi guys, {name} added me here a few months ago to motivate him to do well. Unfortunately, his GPA just fell short of his target one, and so he asked me to post this as a punishment:\n\nCya around~ \n\n\n {kink}'
# bro the kink is the image link
            bot.send_message(group_id, confession)
            bot.send_message(chat_id, "As agreed, we will be sending your confession onto the page.")
            bot.send_photo(group_id, kink)
            # photo = open(kink, 'rb')
            # bot.send_photo(chat_id, photo)

        else:
            msg = ""
            if db.covid.find_one({"private_chat_id": chat_id})["preference"] == "praise":
                msg += 'Good news everyone! name has achieved his goal of getting a GPA better than target goal! I’ll be seeing myself out now, bye~'
            elif db.covid.find_one({"private_chat_id": chat_id})["preference"] == "degenerate":
                msg += f'Hi, name’s GPA this semester is current {new_gpa}. Bye.'
            bot.send_message(db.covid.find_one({"private_chat_id": chat_id})["group_id"], msg)
            # bot.send_message(chat_id, "Congrats on achieving your goal! I am so proud of you.")

        db.covid.find_one_and_delete({"private_chat_id": chat_id})

    except Exception as e:
        print(e)
        msg = bot.send_message(message.chat.id, "There was an error with processing your command.")
        bot.register_next_step_handler(msg, process_receive_gpa)

bot.infinity_polling()
