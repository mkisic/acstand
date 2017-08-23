from PyQt4 import QtGui, uic
from PyQt4.QtCore import QThread, SIGNAL
from threading import Thread
import urllib.request as req
import webbrowser
import datetime
import string
import json
import glob
import bs4
import os

class TreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)

    def __lt__(self, otherItem):
        column = self.treeWidget().sortColumn()
        try:
            return int(self.text(column)) < int(otherItem.text(column))
        except ValueError:
            return self.text(column).lower() < otherItem.text(column).lower()

class getPointsThread( QThread ):
    def __init__ (self, usernames, users, link, official):
        QThread.__init__(self)
        self.usernames = usernames
        self.users = users
        self.link = link
        self.official = official

    def __del__ (self):
        self.wait()

    def message(self, _message):
        QtGui.QMessageBox.information(self, "Status", _message)

    def get_soup(self, url):
        ret = bs4.BeautifulSoup(req.urlopen(url).read(), 'lxml')
        req.urlopen(url).close()
        return ret

    def parse_date(self, s):
        s1 = s[0].split('/')
        s2 = s[1].split(':')
        ret = datetime.datetime(int(s1[0]), int(s1[1]), int(s1[2]), int(s2[0]), int(s2[1]), int(s2[2]))
        return ret

    def get_end_time(self):
        self.emit(SIGNAL("add_in_log(QString)"), "Fetching... contest end time")
        self.soup = self.get_soup(self.link)
        if len(self.soup.findAll(text = "404")):
            self.emit(SIGNAL("add_in_log(QString)"), "Contest does not exist!")
            return 0
        l = self.soup.select('time')
        s = str(l[1].contents)[2:-2].split(' ')
        self.end_time = self.parse_date(s)
        return 1

    def get_user_color(self, username):
        self.emit(SIGNAL("add_in_log(QString)"), "Fetching... " + username + " rating")
        self.soup = self.get_soup("https://atcoder.jp/user/"+username)
        x = self.soup.findAll("dl", { "class" : "dl-horizontal" })
        rating = 0
        try:
            rating = int(x[1].findChildren("span")[1].getText())
            color = "#808080"
        except:
            rating = 0
            color = "#000000"
        
        if rating >= 400:
            color = "#804000"
        if rating >= 800:
            color = "#008000"
        if rating >= 1200:
            color = "#00C0C0"
        if rating >= 1600:
            color = "#0000FF"
        if rating >= 2000:
            color = "#C0C000"
        if rating >= 2400:
            color = "#FF8000"
        if rating >= 2800:
            color = "#FF0000"

        #print (username, rating, color)
        self.users[username]["color"] = color

    def get_user_points(self, username):
        page = 1
        self.emit(SIGNAL("add_in_log(QString)"), "Fetching... " + username + '-' + str(page))
        self.soup = self.get_soup(self.link + "/submissions/all/" + str(page) + "?user_screen_name="+username)
        while not len(self.soup.findAll(text = "There is no submission.")):
            table = self.soup.find("table", { "class" : "table table-bordered table-striped table-wb"})
            rows = table.findChildren('tr')

            for row in rows:
                cells = row.findChildren('td')
                l = []
                for cell in cells:
                    l.append(cell.getText())
                    
                if not len(l):
                    continue
                tmp_time = self.parse_date(l[0].split(' '))

                if (tmp_time - self.end_time).total_seconds() > 0 and self.official:
                    continue

                task = l[1][0]
                try:
                    points = int(l[4])
                except ValueError:
                    continue

                prev = self.users[username][task]
                self.users[username][task] = max(self.users[username][task], points)
                self.users[username]["total"] += self.users[username][task] - prev
                
            page += 1
            self.emit(SIGNAL("add_in_log(QString)"), "Fetching... " + username + '-' + str(page))
            self.soup = self.get_soup(self.link + "/submissions/all/" + str(page) + "?user_screen_name="+username)

    def run(self):
        self.emit(SIGNAL("add_in_log(QString)"), "Start!")
        if not self.get_end_time():
            return
        threads = []
        threads_colors = []
        for username in self.usernames:
            t = Thread(target = self.get_user_points, args=(username,))
            t.start()
            threads.append(t)
            t = Thread(target = self.get_user_color, args=(username,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.emit(SIGNAL("users_dict"), self.users)

        #for user in self.users:
        #    print (user, self.users[user])

class MainWindow( QtGui.QMainWindow ):
    def __init__ (self):
        super( MainWindow, self ).__init__()
        uic.loadUi( 'gui.ui', self )

        self.load_lists()
        
        self.displayButton.clicked.connect( self.display )
        self.createListButton.clicked.connect( self.createList )
        self.donateButton.clicked.connect( self.donate )

    def message(self, _message):
        QtGui.QMessageBox.information(self, "Status", _message)

    def add_in_log(self, s):
        self.listWidget.addItem(s)
        self.listWidget.scrollToItem(self.listWidget.item(self.listWidget.count()-1))

    def done(self):
        self.displayButton.setEnabled(True)
        self.stopButton.setEnabled(False)

        self.add_in_log("Done!")
        self.add_in_log("---------------------------------")

    def donate(self):
        webbrowser.open("https://www.paypal.me/mkisic", new=2)

    def createList(self):
        ListGUI.show()

    def get_soup(self, url):
        ret = bs4.BeautifulSoup(req.urlopen(url).read(), 'lxml')
        req.urlopen(url).close()
        return ret

    def get_users_from_list(self):
        self.users = {}
        f = open("lists/" + self.listName, "r")
        self.usernames = f.readlines()
        f.close()
        for i in range(len(self.usernames)):
            if self.usernames[i][-1] == '\n':
                self.usernames[i] = self.usernames[i][0:-1]

        for username in self.usernames:
            self.users[username]={"user_screen_name":username,"A":0,"B":0,"C":0,"D":0,"E":0,"F":0,"total":0,"color":"#000000"}

        #for user in self.users:
        #    print (user, self.users[user])
    
    def addInTree(self, usernames):
        self.usernames = usernames
        self.displayTree.clear()
        l = []
        for user in self.users:
            tmp_list = [str(self.users[user]["user_screen_name"])]
            col_colors = []
            solved = 0
            for j in range(6):
                tmp_list.append(str(self.users[user][chr(ord('A') + j)]))
                if (int(tmp_list[-1]) > 0):
                    col_colors.append(1)
                    solved += 1
                else:
                    col_colors.append(0)

            tmp_list.append(str(self.users[user]["total"]))
            treeItem = TreeWidgetItem(tmp_list)
            font = QtGui.QFont()
            font.setBold(1)
            treeItem.setFont(0, font)
            color = QtGui.QColor()
            color.setNamedColor(self.users[user]["color"])
            treeItem.setForeground(0, QtGui.QBrush(color))

            for j in range(6):
                if col_colors[j]:
                    treeItem.setForeground(j + 1, QtGui.QBrush(QtGui.QColor(0, 255, 0)))
            l.append(treeItem)

        self.displayTree.addTopLevelItems(l)
        self.displayTree.sortItems(7, 1)

    def display(self):
        self.listName = self.listBox.currentText()
        self.contestType = self.contestTypeBox.currentText()
        self.contestNum = str(self.contestNumBox.value())
        while (len(self.contestNum) < 3):
            self.contestNum = '0' + self.contestNum

        self.link = self.contestType + self.contestNum
        self.link = "https://" + self.link + ".contest.atcoder.jp"

        self.official = self.officialButton.isChecked()

        self.get_users_from_list()
        
        self.get_points_thread = getPointsThread(self.usernames, self.users, self.link, self.official)
        
        self.connect(self.get_points_thread, SIGNAL("users_dict"), self.addInTree)
        self.connect(self.get_points_thread, SIGNAL("finished()"), self.done)
        self.connect(self.get_points_thread, SIGNAL("add_in_log(QString)"), self.add_in_log)

        self.get_points_thread.start()

        self.stopButton.setEnabled(True)

        self.stopButton.clicked.connect(self.get_points_thread.terminate)

        self.displayButton.setEnabled(False)

    def load_lists(self):
        self.listBox.clear()
        l = glob.glob("lists/*")
        for name in l:
            name = name[6::]
            self.listBox.addItem(name)

    def add_list(self, s):
        self.listBox.addItem(s)

class SubWindow( MainWindow ):
    def __init__ (self):
        super( SubWindow, self ).__init__()
        uic.loadUi( 'list_gui.ui', self )
        
        self.valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        self.nameLine.setMaxLength(30)

        self.closeButton.clicked.connect( self.close )
        self.loadButton.clicked.connect( self.load )
        self.saveButton.clicked.connect( self.save )
        self.deleteButton.clicked.connect( self.delete )

    def message(self, _message):
        QtGui.QMessageBox.information(self, "Status", _message)

    def valid(self, s):
        for c in s:
            if not c in self.valid_chars:
                return 0
        return 1

    def delete(self):
        self.usersBox.clear()
        self.list_name = self.nameLine.displayText()
        if not len(self.list_name):
            self.message("Name of the list must not be empty!")
            return
        elif not self.valid(self.list_name):
            self.message("Name of the list contains forbidden characters!")
            return

        try:
            os.remove("lists/" + self.list_name)
            window.load_lists()
        except FileNotFoundError:
            self.message("That list does not exist!")
            return

        self.nameLine.clear()
        self.message("List successfuly deleted!")

    def load(self):
        self.usersBox.clear()
        self.list_name = self.nameLine.displayText()
        if not len(self.list_name):
            self.message("Name of the list must not be empty!")
            return
        elif not self.valid(self.list_name):
            self.message("Name of the list contains forbidden characters!")
            return

        self.users = []
        try:
            f = open("lists/"+self.list_name, "r")
            self.users = f.readlines()
            f.close()
        except FileNotFoundError:
            self.message("That list does not exist!")
            return

        for user in self.users:
            user = "".join(user.split('\n'))
            self.usersBox.append(user)
    
    def save(self):
        self.list_name = self.nameLine.displayText()
        if not len(self.list_name):
            self.message("Name of the list must not be empty!")
            return
        elif not self.valid(self.list_name):
            self.message("Name of the list contains forbidden characters!")
            return
        self.users = self.usersBox.toPlainText().split('\n')
        l = []
        for user in self.users:
            if len(user):
                l.append(user+"\n")

        f = open("lists/"+self.list_name, "w")
        f.writelines(l)
        f.close()

        window.add_list(self.list_name)
        self.message("List successfuly saved!")

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication( sys.argv )
    window = MainWindow()
    ListGUI = SubWindow()
    window.show()
    sys.exit( app.exec_() )
