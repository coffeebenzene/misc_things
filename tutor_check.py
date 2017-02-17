# check for list change
# Add this before f.write(str(ans)) in the test_program

    import copy
    lioriginal = copy.deepcopy(li)
    ans= <function name>(li) # NOTE! remember to add in function name
    list_changed = False
    if len(li) != len(lioriginal):
        list_changed = True
    else:
        for i,j in zip(lioriginal, li):
            if i is not j:
                list_changed = True
                break
    if list_changed:
        ans = str(ans) + " | original list got changed: " + str(li)



# WORKS, BUT IF TRIGGERED, THIS WILL SHOW THE TEST CODE.
# Add this in the {% processor %} block
# This is a naive way to check. The strong way is ast module. which is overkill.
# countTok was supposed to be given in tutor. But apparently it's not. I just copied the code.

banned = {"[::-1]": '"[::-1]"',
          ".reverse(":'".reverse()"',
          "reversed(":'"reversed("',
         }

def input_check(code):
    for search, ban in banned.iteritems():
        if countTok(code, search) > 0:
            return 'Code should not use {}'.format(ban)
    return False

def countTok(code, entry):
   count = 0
   codeLines = code.splitlines()
   for line in codeLines:
      com = line.find('#')
      if com >= 0: line = line[:com]
      count += line.count(entry)
   return count


# Print statement hijacker
import cStringIO
class PrintHijack():
    def __init__(self):
        self._stringio = cStringIO.StringIO()
        self.printed = ""

    def __enter__(self):
        self.prev_stdout = sys.stdout
        sys.stdout = self._stringio
        return self
    
    def __exit__(self, *args):
        sys.stdout = self.prev_stdout
        self.printed = self._stringio.getvalue()
        self._stringio.close()



# Better seeding.
Use either {{ TutorNow }} or {{ nowdate }}, which Django will fill up with a single time when the template is loaded. This will be a string though. (I have tested that it is consistent for all the functions.)
