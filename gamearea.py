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

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GdkPixbuf


def get_reverse_list(list1):
    list2 = []
    for value in list1:
        list2.insert(0, value)

    return list2


COLOR1 = "#4C4B4F"
COLOR2 = "#FFAB00"

if "org.sugarlabs.user" in Gio.Settings.list_schemas():
    settings = Gio.Settings("org.sugarlabs.user")
    colores = settings.get_string("color")
    separados = colores.split(",")

    if len(separados) == 2:
        COLOR1 = separados[0]
        COLOR2 = separados[1]


def get_icon_with_color(icon_name, color="#000000"):
    img_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
        "images/", icon_name + ".svg")

    with open(img_path, "r") as img_file:
        svg = img_file.read()
        svg = svg.replace("fill=\"#000000\"", "fill=\"%s\"" % color)

    pl = GdkPixbuf.PixbufLoader.new_with_type("svg")
    pl.write(svg)
    pl.close()

    return pl.get_pixbuf()


class Cat(object):

    def __init__(self, name, color="#000000"):
        self.color = color
        self.pixbuf = get_icon_with_color(name, color)
        self.x = self.y = 0
        self.width = self.height = 120
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

        self.add_cats()

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK)

        self.connect("motion-notify-event", self.__motion_cb)
        self.connect("button-press-event", self.__press_cb)
        self.connect("button-release-event", self.__release_cb)
        self.connect("draw", self.__draw_cb)

    def __draw_cb(self, widget, context):
        self.__draw_bg(context)
        self.__draw_cats_area(context)
        self.__draw_destination_area(context)

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

            elif y + height > alloc.height:
                y = alloc.height - height

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
        context.line_to(alloc.width / 2, alloc.height)
        context.stroke()

    def add_cats(self):
        cat_ids = range(1, 5)
        colors = [COLOR1, COLOR2]

        for x in range(1, 5):
            cat_id = random.choice(cat_ids)
            cat_name = "cat" + str(cat_id)
            color = random.choice(colors)

            cat_ids.remove(cat_id)
            self.cats.append(Cat(cat_name, color))

    def bring_to_front(self, cat):
        self.cats.remove(cat)
        self.cats.insert(0, cat)

    def redraw(self):
        GObject.idle_add(self.queue_draw)


if __name__ == "__main__":
    win = Gtk.Window()
    win.maximize()
    win.connect("destroy", Gtk.main_quit)

    area = GameArea()
    win.add(area)
    win.show_all()

    Gtk.main()
