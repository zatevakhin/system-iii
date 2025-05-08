# %% Interactive tests for Voice subsystem

# %% Install required dependencies for tests
!pip install git+https://github.com/zatevakhin/voice-forge.git piper-tts

# %% Import required modules
from synthesizer import Synthesizer
import pymumble_py3

# %% Create TTS comnstants
TTS_EN_US_F_AMY_LOW = "en_US-amy-low"
TTS_EN_GB_F_ARU_MED = "en_GB-aru-medium"

# %% Connect client to a Mumble server
mumble = pymumble_py3.Mumble(host="127.0.0.1", user="test")
mumble.set_receive_sound(True)
mumble.start()
mumble.is_ready() # waits connection

# %% Test 1:
Synthesizer(mumble) \
    .tts(TTS_EN_US_F_AMY_LOW) \
    .say("uhm you know like um maybe uh") \
    .silence(0.5) \
    .say("uh uh like i don't know") \
    .run()

# %% Test 2:
Synthesizer(mumble) \
    .tts(TTS_EN_US_F_AMY_LOW) \
    .say("um... could you check") \
    .silence(1.0) \
    .say("my email inbox") \
    .run()

# %% Test 3:
Synthesizer(mumble) \
    .tts(TTS_EN_US_F_AMY_LOW) \
    .say("Turn on the living room lights please") \
    .run()

# %% Test 4:
Synthesizer(mumble) \
    .tts(TTS_EN_GB_F_ARU_MED) \
    .say("I'm so tired today") \
    .run()

# %% Test 5:
Synthesizer(mumble) \
    .tts(TTS_EN_US_F_AMY_LOW) \
    .say("uhm") \
    .silence(0.8) \
    .say("okay so like") \
    .silence(1.2) \
    .say("can you play my playlist") \
    .run()

# %% Test 6:
Synthesizer(mumble) \
    .tts(TTS_EN_US_F_AMY_LOW) \
    .say("Hey can you") \
    .silence(2.0) \
    .say("actually nevermind") \
    .run()

# %% Test 7
Synthesizer(mumble) \
    .tts(TTS_EN_US_F_AMY_LOW) \
    .silence(0.3) \
    .say("Could you open my todays notes") \
    .silence(1.0) \
    .say("in Obsidian, and check what is there") \
    .silence(1.0) \
    .say("just give me summary of notes that I have there") \
    .run()


# %% Test 8
Synthesizer(mumble) \
    .tts(TTS_EN_US_F_AMY_LOW) \
    .say("Roses are blue") \
    .silence(1.0) \
    .say("sky is read") \
    .silence(1.0) \
    .say("hmm.. I need to buy milk eggs and bread.") \
    .run()


# %% Test 9
Synthesizer(mumble) \
    .tts(TTS_EN_US_F_AMY_LOW) \
    .say("I have sent you files") \
    .silence(1.0) \
    .say("in Telegram") \
    .silence(1.0) \
    .say("ah, wait no, in Matrix Chat") \
    .silence(3.0) \
    .say("Could you make summary from those Markdown files") \
    .silence(0.5) \
    .say("and memorize all what is related to ...") \
    .silence(0.5) \
    .say("research about memory in LLMs") \
    .run()

