#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016, Cristian García <cristian99garcia@gmail.com>
#
# This library is free software you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation either
# version 3 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os
import json
import random

from gettext import gettext as _

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GdkPixbuf


class SideType:
    EVEN = 0
    ODD = 1


class GameType:
    DIVIDED_SCREEN = 0
    ROWS = 1


def make_cat_pixbuf(cat_id):
    img_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
        "images/cat" + str(cat_id) + ".svg")

    return GdkPixbuf.Pixbuf.new_from_file(img_path)


def get_reverse_list(list1):
    list2 = []
    for value in list1:
        list2.insert(0, value)

    return list2


class Cat(object):

    def __init__(self, cat_id, width, height):
        self.cat_id = cat_id
        self.pixbuf = make_cat_pixbuf(cat_id)
        self.x = -100
        self.y = -100
        self.width = width
        self.height = height
        self.dragged = False

        if self.width != self.pixbuf.get_width() or self.height != self.pixbuf.get_height():
            self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, GdkPixbuf.InterpType.HYPER)

    def draw(self, context, x=None, y=None):
        if x is not None:
            self.x = x

        if y is not None:
            self.y = y

        Gdk.cairo_set_source_pixbuf(context, self.pixbuf, self.x, self.y)
        context.paint()


class GameArea(Gtk.DrawingArea):

    def __init__(self):
        Gtk.DrawingArea.__init__(self)

        self.line_width = 10
        self.cats = []
        self.selected_cat = None
        self.over_cat = None
        self.selected_option = None
        self.over_option = None
        self.clicked = []
        self.sides = [SideType.EVEN, SideType.ODD]
        self.playing = False
        self.timeout_id = None
        self.count = None
        self.level = 1
        self.levels = {}
        self.level_data = {}
        self.score = 0
        self.high_score = 0
        self.puzzle_count = None
        self.win = True
        self.max_puzzle_count = 5

        with open("levels.json") as file:
            self.levels = json.load(file)

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK)

        self.connect("motion-notify-event", self.__motion_cb)
        self.connect("button-press-event", self.__press_cb)
        self.connect("button-release-event", self.__release_cb)
        self.connect("draw", self.__draw_cb)

    def __draw_cb(self, widget, context):
        self.__draw_bg(context)

        if self.playing:
            if self.level_data["type"] == GameType.DIVIDED_SCREEN:
                self.__draw_lines(context)

            elif self.level_data["type"] == GameType.ROWS:
                self.__draw_selected_option(context)

            self.__draw_timeout(context)
            self.__draw_size_label(context)
            self.__draw_cats(context)
        
        elif self.cats != []:
            self.__draw_end_message(context)        

        elif self.count is not None and not self.playing:
            self.__draw_count(context)

        else:
            self.__draw_welcome_message(context)

    def __motion_cb(self, widget, event):
        alloc = self.get_allocation()
        if self.level_data == {}:
            return

        if self.level_data["type"] == GameType.DIVIDED_SCREEN:
            if self.selected_cat is not None:
                self.selected_cat.dragged = True

                width = self.selected_cat.width
                height = self.selected_cat.height
                x = event.x - width // 2
                y = event.y - height // 2

                left_limit = alloc.width // 2 - self.line_width // 2
                right_limit = alloc.width // 2 + self.line_width // 2
                xcat = self.selected_cat.width // 2 + x

                if x < 0:
                    x = 0

                elif x + width > alloc.width:
                    x = alloc.width - width

                if y < 0:
                    y = 0

                elif y + height > alloc.height - 25:
                    y = alloc.height - height - 25

                if x < left_limit and x + width > left_limit and self.clicked[0] < alloc.width // 2:
                    x = left_limit - width

                elif x + width > right_limit and x < right_limit and self.clicked[0] > alloc.width // 2:
                    x = right_limit

                self.selected_cat.x = x
                self.selected_cat.y = y
                self.clicked = [event.x, event.y]

                self.redraw()

            else:
                selected = False
                for cat in self.cats:
                    if event.x >= cat.x and event.x <= cat.x + cat.width and event.y >= cat.y and event.y <= cat.y + cat.height:
                        self.over_cat = cat
                        selected = True
                        break

                if not selected:
                    self.over_cat = None

        elif self.level_data["type"] == GameType.ROWS:
            if event.x <= alloc.width // 2 - self.line_width // 2:
                new_option = self.sides[0]

            elif event.x >= alloc.width // 2 + self.line_width // 2:
                new_option = self.sides[1]

            else:
                new_option = None

            if new_option != self.over_option:
                self.over_option = new_option
                self.redraw()

    def __press_cb(self, widget, event):
        self.clicked = [event.x, event.y]

        if self.level_data["type"] == GameType.DIVIDED_SCREEN:
            if self.over_cat is not None:
                self.selected_cat = self.over_cat
                self.bring_to_front(self.selected_cat)

                self.redraw()

        if self.level_data["type"] == GameType.ROWS:
            self.selected_option = self.over_option

    def __release_cb(self, widget, event):
        self.clicked = []
        self.selected_cat = None

        if self.level_data["type"] == GameType.ROWS:
            if self.selected_option is not None:
                self.count = 0
                self.redraw()

    def __draw_bg(self, context):
        alloc = self.get_allocation()
        context.set_source_rgb(1, 1, 1)
        context.rectangle(0, 0, alloc.width, alloc.height)
        context.fill()

    def __draw_lines(self, context):
        alloc = self.get_allocation()

        context.set_line_width(self.line_width)
        context.set_source_rgb(0, 0, 0)

        context.move_to(alloc.width // 2, 0)
        context.line_to(alloc.width // 2, alloc.height - 25)
        context.stroke()

    def __draw_cats(self, context):
        for cat in get_reverse_list(self.cats):
            cat.draw(context)

    def __draw_selected_option(self, context):
        alloc = self.get_allocation()
        width = alloc.width // 2 - self.line_width // 2
        height = alloc.height

        context.set_source_rgb(0.9, 0.9, 0.9)

        if self.over_option == self.sides[0]:
            context.rectangle(0, 0, width, height)
            context.fill()

        elif self.over_option == self.sides[1]:
            context.rectangle(alloc.width // 2 + self.line_width // 2, 0, width, height)
            context.fill()

    def __draw_timeout(self, context):
        alloc = self.get_allocation()
        y = alloc.height // 2 - 5

        message = "%s %d %s" % (_("You have left"), self.count, _("seconds"))
        self.show_message(context, message, 20, y)

    def __draw_size_label(self, context):
        alloc = self.get_allocation()

        message1 = _("Even cats")
        message2 = _("Odd cats")
        if self.sides[0] == SideType.ODD:
            backup = message1
            message1 = message2
            message2 = backup

        context.set_source_rgb(0, 0, 0)
        context.set_font_size(20)

        xb, yb, width, height, xa, ya = context.text_extents(message1)
        y = alloc.height // 2 + height // 2
        if self.level_data["type"] == GameType.DIVIDED_SCREEN:
            x = alloc.width // 4 - width // 2
        elif self.level_data["type"] == GameType.ROWS:
            x = alloc.width // 6 - width // 2

        context.move_to(x, y)
        context.show_text(message1)

        xb, yb, width, height, xa, ya = context.text_extents(message2)
        y = alloc.height // 2 + height // 2
        if self.level_data["type"] == GameType.DIVIDED_SCREEN:
            x = alloc.width // 4 * 3 - width // 2
        elif self.level_data["type"] == GameType.ROWS:
            x = alloc.width // 6 * 5 - width // 2

        context.move_to(x, y)
        context.show_text(message2)

    def __draw_count(self, context):
        message = "%s %d %s" % (_("The game will start in"), self.count, _("seconds"))
        y = self.show_message(context, message, 54)
        self.__draw_help_message(context, y + 20)

    def __draw_help_message(self, context, y):
        message = ""
        level = str(self.get_next_level())
        next_level = self.levels[level]

        if next_level["type"] == GameType.DIVIDED_SCREEN:
            message = _("Classify each kind of cat as even or odd")

        elif next_level["type"] == GameType.ROWS:
            message = _("Is the amout of cats on the screen even or odd?")

        self.show_message(context, message, 20, y)

    def __draw_end_message(self, context):
        alloc = self.get_allocation()
        y = 0

        if self.level_data["type"] == GameType.DIVIDED_SCREEN:
            right_cats = 0
            left_cats = 0

            for cat in self.cats:
                if cat.x < alloc.width // 2:
                    left_cats += 1
                else:
                    right_cats += 1

            if left_cats % 2 == self.sides[0]:
                message = _("You correctly placed the cats!")
                self.win = True
            else:
                message = _("You failed to place correctly cats")
                self.win = False
            if self.puzzle_count < self.max_puzzle_count:
                y = self.show_message(context, message, 64)

        elif self.level_data["type"] == GameType.ROWS:
            odd = (len(self.cats) % 2) != 0
            if self.selected_option == int(odd):
                message = _("You selected correctly!")
                self.win = True

            elif self.selected_option != None:
                message = _("You selected wrong")
                self.win = False
            else:
                message = _("You should have selected an option")
                self.win = False
            if self.puzzle_count < self.max_puzzle_count:
                y = self.show_message(context, message, 64)

        if self.puzzle_count < self.max_puzzle_count:
            self.start_timeout(3, self.reset)
            message = "%s %d %s" % (_("The game will restart in"), self.count, _("seconds"))
            y = self.show_message(context, message, 24, y)

            self.__draw_help_message(context, y + 20)

        if self.puzzle_count >= self.max_puzzle_count:
            self.__draw_gameover(context)

    def __draw_welcome_message(self, context):
        message = _("Click on the star to start the game.")
        y = self.show_message(context, message, 64)

        message = _("(And click the star again to stop it)")
        self.show_message(context, message, 24, y)

    def __draw_gameover(self, context):
        if not self.win:
            score = self.score - 20
        else:
            score = self.score
        y = 0
        self.playing = False
        message = _("Game Over")
        y = self.show_message(context, message, 124, -100)
        your_score = "%s %d" % (_("Your Score:"), score)
        y = self.show_message(context, your_score, 60, 50)
        high_score = "%s %d" % (_("High Score:"), score)
        y = self.show_message(context, high_score, 60, 150)
        message = _("Click on the star to start the game.")
        y = self.show_message(context, message, 30, 250)
        self.win = True

    def show_message(self, context, message, font_size, y=0):
        alloc = self.get_allocation()

        context.set_font_size(font_size)
        xb, yb, width, height, xa, ya = context.text_extents(message)

        if width <= alloc.width:
            context.set_source_rgb(0, 0, 0)
            context.move_to(alloc.width // 2 - width // 2, alloc.height // 2 + y)
            context.show_text(message)

            return y + height

        else:
            return self.show_message(context, message, font_size - 5, y)

    def add_cats(self):
        alloc = self.get_allocation()
        cat_ids = list(range(1, 5))
        cats = self.level_data["cats"]
        cats_in_row = 0
        column = 0
        space = 50
        y = -1

        cat_width = 120
        cat_height = 120

        if self.level_data["type"] == GameType.ROWS:
            cat_width = 60
            cat_height = 60

        for x in range(0, cats):
            cat_id = random.choice(cat_ids)
            cat = Cat(cat_id, cat_width, cat_height)

            if self.level_data["type"] == GameType.DIVIDED_SCREEN:
                while cat.x < 0 or cat.x + cat.width > alloc.width or (cat.x < alloc.width // 2 and cat.x + cat.width > alloc.width // 2):
                    cat.x = random.randint(0, alloc.width - cat.width)

                while cat.y < 0 or cat.y + cat.height > alloc.height - 20:
                    cat.y = random.randint(0, alloc.height - cat.height - 25)

            elif self.level_data["type"] == GameType.ROWS:
                if column == cats_in_row:
                    m = 4 if cats_in_row == 5 else 5
                    cats_in_row = min(m, cats - x)
                    column = 0
                    y += 1

                cat.x = alloc.width // 2 - cats_in_row * (cat.width + space) // 2.0 + (cat.width + space) * column + space // 2
                cat.y = y
                column += 1

            self.cats.append(cat)

        if self.level_data["type"] == GameType.ROWS:
            for cat in self.cats:
                cat.y = alloc.height // 2 - cat.height * (column - cat.y)

    def load_level_data(self):
        self.level_data = self.levels[str(self.level)]

    def get_next_level(self):
        level = self.level
        if self.win:
            level = self.level + 1
        
        if level > len(list(self.levels.keys())):
            level = 1

        return level

    def generate_score(self):
        score = self.score
        if self.win:
            score = self.score + 20
        return score

    def bring_to_front(self, cat):
        self.cats.remove(cat)
        self.cats.insert(0, cat)

    def reset(self):
        def cb():
            self.playing = False

        self.puzzle_count += 1
        self.level = self.get_next_level()
        self.score = self.generate_score()
        self.load_level_data()

        if self.level_data["type"] == GameType.DIVIDED_SCREEN:
            random.shuffle(self.sides)

        del self.cats
        self.cats = []
        self.add_cats()
        self.playing = True

        self.start_timeout(15, cb)

    def start(self):
        self.win = True
        self.puzzle_count = 0
        self.level = 1
        self.score = 0
        self.start_timeout(3, self.reset, True)

    def stop(self):
        if self.timeout_id is not None:
            GObject.source_remove(self.timeout_id)
            self.timeout_id = None

        self.playing = False
        del self.cats
        self.cats = []
        self.count = None
        self.redraw()

    def timeout_cb(self, callback=None):
        self.count -= 1
        self.redraw()

        end = self.count <= 0
        self.count = self.count if not end else None
        self.timeout_id = self.timeout_id if not end else None

        if end and callback is not None:
            callback()

        return not end

    def start_timeout(self, time, callback=None, force=False):
        if self.timeout_id is not None and not force:
            return

        elif self.timeout_id is not None and force:
            GObject.source_remove(self.timeout_id)

        self.count = time + 1
        self.timeout_cb()
        self.timeout_id = GObject.timeout_add(1000, self.timeout_cb, callback)

    def redraw(self):
        GObject.idle_add(self.queue_draw)
