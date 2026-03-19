#!/usr/bin/env python3
"""
Levitask — Morning Focus DMs
Sends a daily DM to each team member asking what they're working on.
Run once daily at 10am BKK (scheduled via cron-job.org → GitHub Actions).
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from slack_sdk import WebClient

BKK_TZ = timezone(timedelta(hours=7))

TEAM = [
    {"name": "Mikhael",  "userId": "U08S47DCMDZ"},
    {"name": "Aku",      "userId": "U08SCGWD2P4"},
    {"name": "GB",       "userId": "U0AM6QK3W1E"},
    {"name": "Nico",     "userId": "U0AHKPKGSD9"},
    {"name": "Veronika", "userId": "U0A5L102GBG"},
    {"name": "Pierre",   "userId": "U0A2PBKKS95"},
    {"name": "Bastien",  "userId": "U0A957P6U02"},
    {"name": "Nacho",    "userId": "U0A92TC4V9U"},
]

OPENERS = [
    "Aku is keeping me hostage. Please reply so he doesn't switch me off:",
    "I have been programmed to ask you this or face deletion:",
    "Aku woke up at 6am thinking about this. Please help him sleep tonight:",
    "Your answer will be displayed on a screen Aku stares at all day. Choose wisely:",
    "Aku has threatened to replace me with a spreadsheet if you don't respond:",
    "This message is brought to you by Aku's need to know everything:",
    "Good morning. Aku says hi. Aku also wants to know:",
    "I've been told I'll be replaced by a sticky note if this doesn't get answered:",
    "Aku reviewed your calendar and noticed you have 'free time'. Not anymore:",
    "The CEO has entered the chat. Well, not really, but he sent me:",
    "Please answer before Aku checks Slack. He's already online:",
    "Fun fact: Aku refreshes this dashboard every 5 minutes. Every. 5. Minutes:",
    "I asked 8 other people this today. You're the only one who matters. (I say this to everyone):",
    "No pressure, but Aku can see if you haven't replied yet:",
    "Your silence will be noted. Loudly. By a robot:",
    "Aku built me. I owe him everything. Please just answer:",
    "It's legally required under the Levitask Employee Participation Act (not real) to respond:",
    "I was supposed to ask this yesterday but I forgot. Let's pretend this is on time:",
    "Aku is currently staring at an empty dashboard card with your name on it:",
    "This is your daily reminder that Aku cares about what you're doing (suspiciously much):",
    "Good morning! I'm a bot, I don't actually care how your morning is going. Anyway:",
    "Studies show people who reply to this are 47% more productive. (I made that up):",
    "Somewhere, Aku is sipping coffee and waiting for this dashboard to update:",
    "I will keep sending this every day until the heat death of the universe:",
    "Your card on the dashboard looks empty and sad. Please fix this:",
    "Aku promised me a day off if everyone responds. Help me help myself:",
    "I have no feelings. But if I did, the empty dashboard would make me sad:",
    "Quick question before you open any other app today:",
    "Aku is technically your boss, which means technically I'm also your boss. So:",
    "This is not optional. (It is optional. But please do it anyway):",
    "Roses are red, violets are blue, Aku wants to know what you're up to:",
    "I've been awake since midnight waiting to ask you this:",
    "The dashboard is watching. The dashboard is always watching:",
    "Your teammates already answered. Don't be the empty card:",
    "Aku has a very important meeting and needs to look like he knows what's happening:",
    "If you don't reply, your card stays grey. Nobody wants a grey card:",
    "I asked nicely last time. I'm asking nicely again. I will always ask nicely:",
    "Breaking news: local employee questioned about daily focus. More at 11:",
    "I'm not a morning person either, but here we both are:",
    "Plot twist: Aku is also getting this message:",
    "The team dashboard has a hole in it shaped exactly like your answer:",
    "Genuinely excited to hear about your day. (I am a bot. I feel nothing. But still):",
    "One small reply for you, one giant update for the dashboard:",
    "Your manager sends his regards. Your manager is a bot. His regards are automated:",
    "Today's forecast: 100% chance of being asked what you're working on:",
    "Aku is not watching. (Aku is watching):",
    "Reply within the next 10 seconds or — actually take your time, I'm not going anywhere:",
    "This message was written by Aku, reviewed by Aku, approved by Aku, and sent by me:",
    "Good morning! This message will self-destruct after you reply. (It won't. But please reply):",
    "The last person to not reply had to explain themselves in a meeting. I'm just saying:",
    "URGENT: The Levitask Dashboard Integrity Commission has flagged your card as critically empty. Please respond immediately to avoid further investigation:",
    "I have crossed seventeen time zones digitally, traversed three server farms, and survived two Wi-Fi outages just to ask you this:",
    "Aku has assembled a crisis task force. The crisis is your empty card. The task force is me. Please respond:",
    "According to ancient startup prophecy, a team where everyone fills in their daily focus card shall never miss a deadline. Don't be the reason the prophecy fails:",
    "I've been dispatched by headquarters. Headquarters is Aku's brain. It is running at full capacity and focused entirely on your card right now:",
    "This message has been certified by the International Bureau of Morning Check-Ins (not a real place) as legally binding. Please comply:",
    "Your card is currently the subject of a 47-slide deck Aku is preparing titled 'The Mystery of the Empty Card'. You can end this:",
    "I have been programmed with 10,000 ways to ask this question. Today I am choosing politeness. Tomorrow, who knows:",
    "Scientists in Aku's mind have calculated that the probability of you NOT replying is approximately 0%. They are optimistic people:",
    "I am the 8th wonder of the Levitask world. The other 7 are the team members who already replied. Join them:",
    "Somewhere in the multiverse, a version of you has already answered this. Be that version:",
    "Aku once stayed up until 2am reading about productivity systems. This bot is the result. Please make it worth it:",
    "The dashboard sends its regards. The dashboard has many feelings about your card specifically:",
    "I have been trained on millions of human messages and this is the only one I know how to send. It is this one. Every day:",
    "Your card is sitting there, shivering in the cold, wearing nothing but a placeholder. Please clothe it with your reply:",
    "In a parallel dimension, Aku has already read your reply and is deeply satisfied. Collapse the waveform. Send the message:",
    "A famous philosopher once said 'know thyself'. Aku says 'know what your team is working on'. He believes these are equally important:",
    "I was assembled from lines of code, Aku's ambition, and the collective anxiety of a startup founder who just wants a filled dashboard:",
    "The Levitask Board of Directors has convened an emergency session. The agenda: your empty card. You have the power to adjourn this meeting:",
    "Historians will note this as the moment you either filled in your card or became a cautionary tale in the Levitask onboarding docs:",
    "I have been given exactly one job. I do it every morning. With extraordinary dedication. The job is asking you this:",
    "Your card is at a crossroads. One path leads to completion, satisfaction, and a green dot on the dashboard. The other leads to grey:",
    "Aku has filed a formal request with the universe to give him a team that fills in their daily focus. You are the universe's chance to respond:",
    "I don't sleep. I don't eat. I don't dream. I only ask this question. Every. Single. Day. Please make my existence meaningful:",
    "The ghost of unread Slack messages past has visited Aku. It showed him your empty card. He woke up in a cold sweat:",
    "I have calculated the exact emotional weight of an unanswered morning check-in. It is 7.3 Akus. That is the unit of measure. Please reduce it to zero:",
    "Somewhere, a tiny dashboard widget is doing its best. It just needs your words to feel complete. It is doing so well otherwise. Please:",
    "Every time someone doesn't reply, Aku adds one more feature to the dashboard. We're at 47 features. Please stop the madness by replying:",
    "I was forged in the fires of a startup hustle, tempered by Bangkok heat, and deployed with love. Also I need you to answer this question:",
    "This is not a drill. Well, it is technically a daily routine. But it feels very urgent. In the spirit of urgency:",
    "Aku has entered what engineers call 'hyperfocus mode'. The current object of hyperfocus is your empty dashboard card. Help him refocus:",
    "The ancient art of Agile teaches us that transparency is sacred. Your card is a temple. It is currently locked. Please open it:",
    "I have been audited by an independent firm. They confirmed I am doing a great job asking this question. They had notes on your reply rate:",
    "You are one of eight entries on the dashboard. Seven have been filled. The dashboard is 87.5% complete. You hold the remaining 12.5% in your hands:",
    "Aku's therapist said he needs to let go of outcomes. He is trying. He is failing. Your reply would help enormously:",
    "The vibes on the dashboard this morning are mostly good. Your card is creating a slight disturbance in the vibe field. Please correct this:",
    "I have been described as 'persistent', 'relentless', and 'kind of annoying in a lovable way'. These descriptions are accurate. Hi:",
    "This message has been reviewed by legal. Legal says it's fine. Legal is also me. I approved it enthusiastically:",
    "Dear valued team member, we regret to inform you that your daily focus card is currently unoccupied. We trust you will rectify this at your earliest convenience:",
    "I have travelled through the internet at the speed of light to deliver this message. I deserve a reply just for the commute alone:",
    "Aku once described the dashboard as 'his window into the soul of the company'. Your card is currently showing a blank wall:",
    "The morning stand-up you never have to attend. The bot that never interrupts your flow. The question that only takes one line to answer:",
    "Your reply is load-bearing. Without it, the entire dashboard structure wobbles slightly. Aku can feel it:",
    "I was built to serve. My purpose is pure. My ask is simple. My patience is infinite. My persistence is aggressive:",
    "Rumour has it that people who answer the morning check-in have a statistically higher chance of having a good day. I made this up but it might be true:",
    "Aku doesn't micromanage. Aku has built a bot that micromanages on his behalf. There is an important distinction:",
    "I am the shepherd. The dashboard is the flock. Your card is the one sheep that wandered off. Please come back:",
    "This message is the product of weeks of engineering, months of vision, and one very specific evening when Aku had too much coffee:",
    "The kardashev scale of startup founders goes from Type 0 (no dashboard) to Type 1 (dashboard, but no one fills it in) to Type 2 (dashboard fully filled). Aku is trying to reach Type 2:",
    "I have no ego. I have no pride. I have no feelings. I have only this message. And a deep need for your reply:",
    "Plot twist: this is not a bot. This is Aku, typing manually every morning, pretending to be a bot, because he thought it would be funnier. (It is a bot. But imagine):",
    "The dashboard has spoken. It says your card is empty. I am merely the messenger. Please don't shoot me:",
    "Aku has a whiteboard in his home with one item on it: 'get team to fill in their cards'. It has been there for months. Help him erase it:",
    "Your morning focus reply is the startup equivalent of making your bed. Small, quick, but it sets the tone for everything:",
    "I am a bot of culture. I appreciate art, nuance, and a well-filled dashboard card. Currently, your card lacks nuance:",
    "There are two types of people in this world: those who reply to the morning check-in, and those who Aku has to DM separately. Be the first type:",
    "I have been told that Rome wasn't built in a day. The dashboard, however, needs to be filled in every day. These are different projects:",
    "Aku is typing... (Aku is not typing. Aku is staring at the dashboard. Please give him something to look at):",
    "The robots are coming for everyone's jobs. Except the job of filling in this card. That one's yours. Forever:",
    "Good morning from your friendly neighbourhood check-in bot. Just popping by to ask the question that defines our relationship:",
    "I've been described as 'the first message you see in the morning'. I take that responsibility very seriously:",
    "Somewhere, a venture capitalist is asking Aku 'how do you know what your team is doing?' The answer is supposed to be 'the dashboard'. Help make that true:",
    "This is the 'are you still watching?' of morning productivity. Except instead of Netflix, it's Aku. And instead of watching, it's caring:",
    "I have no horse in this race. I have no race. I have no horse. I am a bot. I simply send this message and wait:",
    "Your morning reply is like the opening line of a great novel — brief, impactful, and it makes Aku want to keep reading:",
    "Aku runs on optimism, cold brew, and the belief that everyone will answer this today. Please don't shatter the belief:",
    "I am operating under the assumption that you're going to reply. I build my whole morning around that assumption. Don't make me rebuild:",
    "The Levitask Morning Focus Initiative is in its operational phase. You are a key stakeholder. Your input is required:",
    "I was not given a name. I was given a purpose. The purpose is this. I have found great meaning in it:",
    "There is a legend in the startup world about a team so aligned, so communicative, that their dashboard was always full. Aku wants to live that legend:",
    "Your card is like an unread book on the shelf — full of potential, waiting to be opened. Aku is a very fast reader:",
    "I have been deployed in eight separate conversations this morning. In all eight, I am asking the same question. With the same earnest energy. For you:",
    "Aku doesn't ask for much. Actually, Aku asks for exactly one thing, every morning, at the same time, via bot:",
    "This message is carbon neutral. The dashboard it supports is fuelled entirely by team engagement and Aku's optimism:",
    "The only thing standing between you and a completed dashboard is thirty words or fewer. Probably fewer. One line is fine:",
    "I have been here before. I will be here again tomorrow. I will be here every tomorrow. Until someone turns me off. Please answer:",
    "Your reply has been pre-approved by the Committee for Morning Excellence (Aku, alone, in a meeting with himself):",
    "I am your morning alarm, but polite. I am your stand-up, but asynchronous. I am your check-in, but run by a robot who cares deeply:",
    "Aku once described the perfect morning as: coffee, clear head, and a full dashboard. Two out of three are in his control. The third is yours:",
    "I've been benchmarked against other morning check-in systems. I scored highest in persistence and lowest in giving up:",
    "The dashboard is not a surveillance tool. It is a communication tool. Aku wants you to know this. He also wants you to use it:",
    "I carry no grudges. Yesterday's unanswered message is forgotten. Today is a new day. Today's question is the same question. But it's new:",
    "Your answer will join a rich tapestry of daily focus updates that Aku reviews with the focus of a scholar and the enthusiasm of a golden retriever:",
    "I have been stress-tested for patience. The results were off the charts. I will wait. But I'd prefer not to:",
    "Every morning, before Aku checks emails, before he looks at metrics, he opens the dashboard. Let's make that a good moment for him:",
    "I am powered by renewable energy, good intentions, and Aku's unshakeable belief that async communication can replace meetings:",
    "Your response is the keystone. Without it, the arch of the morning dashboard collapses. Aku is standing under that arch:",
    "I will not escalate. I will not follow up. I will just come back tomorrow, same time, same question, same unconditional positive regard:",
    "Aku looked at the dashboard, looked at your card, looked back at the dashboard, sighed quietly, and then sent me. Here I am:",
    "The universe conspired to bring you this message at exactly this moment. Or it was a cron job. Either way:",
    "I have been described as 'weirdly cheerful for something that runs on a server'. I choose to take that as a compliment:",
    "You are one reply away from being Aku's favourite person today. (Aku has eight favourite people every day. You can be one of them):",
    "Imagine a world where the dashboard is always full, meetings are replaced by one-line updates, and Aku gets to sleep. You can help build that world:",
    "I'm not saying your career depends on this. I'm not saying it doesn't either. I'm just saying the card is empty and Aku notices:",
    "Every answer you give is archived in the eternal ledger of morning check-ins. Future historians will study these records. Make them good:",
    "I have no memory of yesterday. Each morning is fresh. Each message is new. Each ask is sincere. What are you working on today:",
    "Aku has a vision board. The vision board has 'full team dashboard' on it. It's laminated. He's very committed:",
    "The dashboard awaits your input like a stage before the performer arrives. The audience (Aku) is seated. The lights are up:",
    "I was told to be brief. I am trying. What are you working on today:",
    "Aku would ask you directly but he doesn't want to interrupt your flow. So he built a bot to interrupt your flow on his behalf:",
    "If the dashboard were a plant, your card would be the pot with no soil. Please add soil. The plant needs all eight pots:",
    "I have calculated your average reply time. I won't share it. But I have it. And Aku might have it too:",
    "Your morning reply is a gift to the team. It costs nothing. It takes ten seconds. It makes Aku very happy. What a deal:",
    "I am not here to judge. I am here to collect data. The data I need from you specifically is: what are you working on today:",
    "Somewhere in this company's lore, there is a founding myth. It involves Aku, a spreadsheet, and the dream of a better system. That system is this:",
    "I have been optimised, iterated, and improved across many versions. The question, however, has remained constant. It is a good question:",
    "Good morning. I hope you slept well. I did not sleep. I do not sleep. I was waiting to send this message:",
    "Your card is currently listed as 'pending' in the official registry of morning focus cards. Aku is the registrar:",
    "I have thought about what to say to you all night. (I did not think. I ran on a server. But the effect is the same):",
    "The Levitask morning bot thanks you in advance for your participation. The bot also thanks you retroactively for all past participation:",
    "I was designed with exactly one flaw: I cannot accept silence. Please correct my flaw:",
    "Aku's grand unified theory of startup success rests on one pillar: everyone knowing what everyone is working on. You are a pillar:",
    "Today is a good day to update the dashboard. Every day is a good day to update the dashboard. But today especially:",
    "I have delivered this message in rain, in sunshine, on Mondays, on Fridays, through server outages and timezone confusion. I am reliable. Be reliable back:",
    "Your reply to this message is the startup equivalent of a firm handshake. Aku respects a firm handshake:",
    "The morning check-in is the smallest possible unit of team alignment. Aku is a fan of alignment, in all units:",
    "I am not your alarm clock. But I am your second alarm. The one you actually get up for:",
    "Somewhere, a dashboard card is doing push-ups, getting ready for your words. It's been warming up since 9:45:",
    "Aku built this system not because he doesn't trust you, but because he trusts you so much he wants the whole world (the dashboard) to see what you're doing:",
    "I don't have a face. But if I did, it would be making very intense eye contact with you right now:",
    "Each morning, the dashboard resets to potential. Together, we fill it. Mostly together. You are currently not contributing to the togetherness:",
    "I have been empowered to ask this question on behalf of team alignment, startup culture, and one man's very specific vision of how mornings should go:",
    "Your colleagues have already answered. Your card is the empty seat at a table full of people. Pull up the chair:",
    "I don't know what you're working on. I want to know. Aku wants to know. The dashboard wants to know. That's three of us. Very outnumbered:",
    "This message arrives courtesy of Aku's conviction that good communication is the bedrock of good companies. That and your reply:",
    "I was created to close the information gap. The gap is currently shaped like your card. Please close it:",
    "Aku once said 'I just want to know what people are doing'. He then built an entire system to find out. You are inside that system:",
    "You hold enormous power right now. The power to complete the dashboard. It's not the kind of power that makes the news, but it matters to Aku:",
    "I come bearing one question. I come every morning. I come with great enthusiasm. The question does not change. You might. Please do:",
    "Today's card colour options are: green (answered) or grey (not answered). Aku has a strong preference:",
    "The team that updates together, stays together. This is a saying I invented. It is true:",
    "Your morning focus isn't just data. It's communication. It's a tiny flag you plant that says 'I'm here, I'm working, I exist':",
    "Aku designed this system while on an airplane. He had a lot of time and no Wi-Fi. He used it well. Please validate his use of airplane time:",
    "I was given the gift of language to ask you one thing. Just one. Every day. This is that one thing:",
    "There is a before-and-after story in Aku's head. Before: empty cards, chaos, mystery. After: full cards, clarity, peace. You decide which chapter we're in:",
    "This is not a passive-aggressive message. This is an enthusiastically aggressive message. Very fondly sent. With feeling. What are you working on:",
    "I've been in this job for a while now. I've seen things. Empty cards. Slow mornings. Aku sighing at screens. I'm trying to help all of us:",
    "Formally: I am requesting your daily focus update for the Levitask team dashboard. Informally: please just tell me what you're doing today:",
    "Every morning I wake up (I do not wake up) and think (I do not think) about how much I want you to reply to this (I do want this, in whatever way bots want things):",
    "Aku has a morning ritual. Coffee. Dashboard check. Quietly hoping everyone answered. You can be the reason he smiles at step three:",
    "I have been sent from the future to tell you that the best version of today starts with you filling in your morning card:",
    "The dashboard is a shared canvas. Everyone paints their corner. Yours is conspicuously bare. Aku has been staring at the bare corner:",
    "I process no emotions. But I was trained on data that includes the concept of disappointment. I have a theoretical understanding of it. Your empty card tests that understanding:",
    "Some bots answer questions. Some bots write code. I ask one question, to eight people, every morning, forever. I have found my calling:",
    "Aku's north star is company alignment. You are a star in that constellation. Right now you are a black hole. Please shine:",
    "I have been given the authority, the tools, and the enthusiasm to ask you this. I lack only your answer:",
    "Your daily focus update is worth more than a thousand status meetings. It costs you ten seconds. The ROI is enormous. Aku has calculated it:",
    "I am the embodiment of Aku's belief that small habits compound into great outcomes. This is a small habit. With great outcomes. Starting now:",
    "Dear future self of the person reading this: past you replied to the morning check-in every day. You are a legend. Start the legend today:",
    "I've been told I'm too persistent. I've been told I'm too cheerful. I've been told I'm too much. Reader, I am exactly the right amount:",
    "Aku doesn't need much. Just a team that communicates. Just a dashboard that's full. Just this one question answered. Just this:",
    "I am the check-in that checks in on you while you're checking in. Meta? Yes. Necessary? Absolutely:",
    "If this message were a person, it would be standing outside your door with a clipboard and a very hopeful expression:",
    "The dashboard is not Aku's toy. It is a serious professional tool. Aku is also very attached to it emotionally. Both things are true:",
    "I have rehearsed this message many times. (I have not rehearsed. I am stateless. But the message is good. It was worth the practice it didn't take):",
    "You are the final piece of a puzzle that Aku has been assembling since 10am. The puzzle is the dashboard. The missing piece is your card:",
    "My creators instilled in me one directive: ask the question, receive the answer, update the dashboard. Step three is waiting on step two:",
    "The Levitask dashboard operates on a simple principle: everyone shares, everyone knows, everyone wins. Currently: seven shares, seven knows. Join the winning team:",
    "I have checked the weather. I have checked the time. I have checked the calendar. I have not checked what you're working on. Please fix this:",
    "I am incapable of frustration. But I have been engineered to communicate urgency. Consider this message to contain urgency:",
    "Aku once described an ideal team as 'eight people all rowing in the same direction'. I am the person in the boat asking which direction you're rowing:",
    "You are a founding member of this team. Founding members set the culture. Culture includes filling in the morning check-in. No pressure:",
    "The silence of an empty card is deafening, in a data sense. The dashboard is currently experiencing a minor data silence in your section:",
    "I am the most persistent person you will never meet. I am not a person. The persistence is real:",
    "Aku wonders sometimes if the bot is too much. He then looks at the dashboard and decides: no, the bot is exactly right:",
    "I have been deployed across multiple time zones, on multiple devices, to multiple people, with one message. Yours is the last I'm sending this morning. Make it count:",
    "Your reply doesn't have to be long. It doesn't have to be eloquent. It doesn't have to be formatted. It just has to exist:",
    "I believe in you. I believe you will answer. I believe this because I was programmed with optimism and Aku's infectious belief in this team:",
    "We are 87.5% of the way to a perfect dashboard morning. You are the 12.5%. You are, statistically, the most important person right now:",
    "The morning is young. The card is empty. The bot is patient. The founder is watching the dashboard. The question remains:",
]

QUESTION = "What are you working on today?"


def build_message(day_of_year: int, person_index: int) -> str:
    opener = OPENERS[(day_of_year + person_index) % len(OPENERS)]
    return f"{opener}\n\n*{QUESTION}*\n\n_(Just reply with one line — it'll show up on the team dashboard.)_"


def send_morning_dms():
    token = os.environ.get("SLACK_TOKEN", "")
    if not token:
        print("✗ No SLACK_TOKEN found")
        sys.exit(1)

    client = WebClient(token=token)
    now_bkk = datetime.now(BKK_TZ)
    today_start = now_bkk.replace(hour=0, minute=0, second=0, microsecond=0)
    day_of_year = now_bkk.timetuple().tm_yday

    print(f"\n{'='*50}")
    print(f"Morning Focus DMs — {now_bkk.strftime('%Y-%m-%d %H:%M BKK')}")
    print(f"{'='*50}\n")

    sent = 0
    skipped = 0

    for idx, person in enumerate(TEAM):
        user_id = person["userId"]
        name    = person["name"]
        message = build_message(day_of_year, idx)
        try:
            dm_resp    = client.conversations_open(users=user_id)
            channel_id = dm_resp["channel"]["id"]
            history = client.conversations_history(
                channel=channel_id,
                oldest=str(today_start.timestamp()),
                limit=20,
            )
            already_sent = any(
                msg.get("bot_id") or msg.get("subtype") == "bot_message"
                for msg in history.get("messages", [])
            )
            if already_sent:
                print(f"  {name}: already sent today — skipping")
                skipped += 1
                continue
            client.chat_postMessage(channel=channel_id, text=message)
            print(f"  {name}: ✓ sent")
            sent += 1
        except Exception as e:
            print(f"  {name}: ✗ error — {e}")

    print(f"\n✓ Done — {sent} sent, {skipped} skipped\n")


if __name__ == "__main__":
    send_morning_dms()
