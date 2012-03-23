import smtpd
import asyncore

smtp = smtpd.DebuggingServer(('localhost', 1957), None)

try:
    asyncore.loop()
except KeyboardInterrupt:
    pass
