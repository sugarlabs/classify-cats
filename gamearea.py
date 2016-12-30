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
import random

from gettext import gettext as _

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GdkPixbuf


class CatType:
    SEATED = 0
    STANDING = 1


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

    def __init__(self, cat_id):
        self.cat_id = cat_id
        self.cat_type = CatType.SEATED if cat_id in [2, 3] else CatType.STANDING
        self.pixbuf = make_cat_pixbuf(cat_id)
        self.x = 0
        self.y = 0
        self.width = self.pixbuf.get_width()
        self.height = self.pixbuf.get_height()
        self.dragged = False

    def draw(self, context, x=None, y=None):
        if x != None:
            self.x = x

        if y != None:
            self.y = y

        Gdk.cairo_set_source_pixbuf(context, self.pixbuf, self.x, self.y)
        context.paint()


class GameArea(Gtk.DrawingArea):

    def __init__(self):
        Gtk.DrawingArea.__init__(self)

        self.line_width = 10
        self.cats_area_height = 150
        self.cats = []
        self.selected_cat = None
        self.over_cat = None
        self.clicked = []
        self.sides = [CatType.SEATED, CatType.STANDING]
        self.playing = False
        self.timeout_id = None
        self.count = None

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
            self.__draw_cats_area(context)
            self.__draw_destination_area(context)
            self.__draw_timeout(context)

        elif self.cats != []:
            self.__draw_end_message(context)

        elif self.count != None and not self.playing:
            self.__draw_count(context)

        else:
            self.__draw_welcome_message(context)

    def __motion_cb(self, widget, event):
        alloc = self.get_allocation()

        if self.selected_cat is not None:
            self.selected_cat.dragged = True
            width = self.selected_cat.width
            height = self.selected_cat.height
            x = event.x - width / 2
            y = event.y - height / 2

            left_limit = alloc.width / 2 - self.line_width / 2
            right_limit = alloc.width / 2 + self.line_width / 2
            xcat = self.selected_cat.width / 2 + x

            if x < 0:
                x = 0

            elif x + width > alloc.width:
                x = alloc.width - width

            if y < self.cats_area_height + self.line_width:
                y = self.cats_area_height + self.line_width

            elif y + height > alloc.height - 25:
                y = alloc.height - height - 25

            if x < left_limit and x + width > left_limit and self.clicked[0] < alloc.width / 2:
                x = left_limit - width

            elif x + width > right_limit and x < right_limit and self.clicked[0] > alloc.width / 2:
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

    def __press_cb(self, widget, event):
        self.clicked = [event.x, event.y]

        if self.over_cat is not None:
            self.selected_cat = self.over_cat
            self.bring_to_front(self.selected_cat)

            self.redraw()

    def __release_cb(self, widget, event):
        self.clicked = []
        self.selected_cat = None

    def __draw_bg(self, context):
        alloc = self.get_allocation()
        context.set_source_rgb(1, 1, 1)
        context.rectangle(0, 0, alloc.width, alloc.height)
        context.fill()

    def __draw_cats_area(self, context):
        alloc = self.get_allocation()
        space = 50
        cats = 0
        for cat in self.cats:
            cats += 1 if not cat.dragged else 0

        total_width = self.cats[0].width * cats + space * (cats - 1)

        x = alloc.width / 2 - total_width / 2
        y = self.cats_area_height / 2 - self.cats[0].height / 2

        for cat in get_reverse_list(self.cats):
            if not cat.dragged:
                cat.draw(context, x, y)
                x += cat.width + space

            else:
                cat.draw(context)

    def __draw_destination_area(self, context):
        alloc = self.get_allocation()

        context.set_line_width(self.line_width)
        context.set_source_rgb(0, 0, 0)

        context.move_to(0, self.cats_area_height + self.line_width / 2)
        context.line_to(alloc.width, self.cats_area_height + self.line_width / 2)
        context.stroke()

        context.move_to(alloc.width / 2, self.cats_area_height)
        context.line_to(alloc.width / 2, alloc.height - 25)
        context.stroke()

    def __draw_timeout(self, context):
        alloc = self.get_allocation()
        y = alloc.height / 2 - 5

        message = "%s %d %s" % (_("You have left"), self.count, _("seconds"))
        self.show_message(context, message, 20, y)

    def __draw_count(self, context):
        message = "%s %d %s" % (_("The game will start in"), self.count, _("seconds"))
        self.show_message(context, message, 54)

    def __draw_end_message(self, context):
        alloc = self.get_allocation()
        matched = 0

        for cat in self.cats:
            side = 0 if cat.x < alloc.width else 1
            if cat.cat_type == self.sides[side] and cat.dragged:
                matched += 1

        if matched == 4:
            message = _("You matched all cats well!")
        else:
            message = "%s %d %s" % (_("You matched"), matched, _("cats well."))

        y = self.show_message(context, message, 64)

        self.start_timeout(3, self.reset)
        message = "%s %d %s" % (_("The game will restart in"), self.count, _("seconds"))
        self.show_message(context, message, 24, y)

    def __draw_welcome_message(self, context):
        message = _("Click on the star to start the game.")
        y = self.show_message(context, message, 64)

        message = _("(And click the star again to stop it)")
        self.show_message(context, message, 24, y)

    def show_message(self, context, message, font_size, y=0):
        alloc = self.get_allocation()

        context.set_font_size(font_size)
        xb, yb, width, height, xa, ya = context.text_extents(message)

        if width <= alloc.width:
            context.set_source_rgb(0, 0, 0)
            context.move_to(alloc.width / 2 - width / 2, alloc.height / 2 + y)
            context.show_text(message)

            return y + height

        else:
            return self.show_message(context, message, font_size - 5, y)

    def add_cats(self):
        cat_ids = range(1, 5)

        for x in range(1, 5):
            cat_id = random.choice(cat_ids)
            cat_ids.remove(cat_id)
            self.cats.append(Cat(cat_id))

    def bring_to_front(self, cat):
        self.cats.remove(cat)
        self.cats.insert(0, cat)

    def reset(self):
        def cb():
            self.playing = False

        del self.cats
        self.cats = []
        random.shuffle(self.sides)
        self.add_cats()
        self.playing = True

        self.start_timeout(5, cb)

    def start(self):
        self.start_timeout(3, self.reset, True)

    def stop(self):
        if self.timeout_id != None:
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

        if end and callback != None:
            callback()

        return not end

    def start_timeout(self, time, callback=None, force=False):
        if self.timeout_id != None and not force:
            return

        elif self.timeout_id != None and force:
            GObject.source_remove(self.timeout_id)

        self.count = time + 1
        self.timeout_cb()
        self.timeout_id = GObject.timeout_add(1000, self.timeout_cb, callback)

    def redraw(self):
        GObject.idle_add(self.queue_draw)
