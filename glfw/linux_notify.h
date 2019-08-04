/*
 * Copyright (C) 2019 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the GPL3 license.
 */

#pragma once


#include "dbus_glfw.h"
#include "internal.h"

typedef unsigned long long notification_id_type;
typedef void (*GLFWDBusnotificationcreatedfun)(notification_id_type, uint32_t, void*);
typedef void (*GLFWDBusnotificationactivatedfun)(uint32_t, const char*);
notification_id_type
glfw_dbus_send_user_notification(const char *app_name, const char* icon, const char *summary, const char *body, const char *action_name, int32_t timeout, GLFWDBusnotificationcreatedfun, void*);
void
glfw_dbus_set_user_notification_activated_handler(GLFWDBusnotificationactivatedfun handler);
