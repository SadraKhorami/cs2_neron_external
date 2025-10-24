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
								state="khorami.dev",
								details="Counter-Strike 2 best story mode game",
								start=int(time.time()),
								large_image="cpunk",
								large_text="cpunk",
								small_image="cpunk",
								small_text="cpunk on top",
								buttons=[{'label': 'website', 'url': 'khorami.dev/cpunk'}]
							)
						except Exception as e:
							pass
					a = True
					time.sleep(1)
				else:
					time.sleep(1)
		except:
			time.sleep(30)