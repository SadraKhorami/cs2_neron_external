from pypresence import Presence
import time

def DiscordRpcThread(Options):
	while True:
		try:
			presence = Presence(1277586728517107744)
			presence.connect()
			a = False
			while True:
				if Options["EnableDiscordRPC"]:
					if not a:
						try:
							presence.update(
									state="cs2_neron_external",
									details="External CS2 research tool — ESP · Aimbot · Triggerbot (analysis only)",
									start=int(time.time()),
									large_image="cs2_neron",
									large_text="cs2_neron_external",
									small_image="khorami",
									small_text="khorami.dev",
									buttons=[{'label': 'Project page', 'url': 'https://github.com/SadraKhorami/cs2_neron_external'}]
								)
						except Exception as e:
							pass
					a = True
					time.sleep(1)
				else:
					time.sleep(1)
		except:
			time.sleep(30)