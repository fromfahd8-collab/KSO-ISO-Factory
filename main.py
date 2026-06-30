#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# مشروع: KSO-ISO-Factory
# الوصف: ينشئ مجلد .github/workflows/ وملف build.yml لبناء ISO لايف
# برمجة عبد الله و عبد الرحمن هاني [KSO]

import os

# محتوى ملف build.yml
BUILD_YML = """\
name: KSO-HANI V34.FINAL11 - ISO Factory [KSO]

on:
  workflow_dispatch:

jobs:
  build-iso:
    name: بناء ISO لايف KSO-HANI V34.FINAL11
    runs-on: ubuntu-24.04

    steps:

      # الخطوة 1: تثبيت أدوات البناء
      - name: تثبيت أدوات البناء
        run: |
          sudo apt-get update -y
          sudo apt-get install -y debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools

      # الخطوة 2: بناء النظام الأساسي Ubuntu Noble 24.04
      - name: بناء النظام الأساسي debootstrap
        run: |
          sudo debootstrap --arch=amd64 noble rootfs

      # الخطوة 3: تثبيت البرامج الإجبارية داخل النظام
      - name: تثبيت البرامج داخل النظام
        run: |
          sudo chroot rootfs /bin/bash -c "
            apt-get update -y && \\
            apt-get install -y --no-install-recommends \\
              linux-generic \\
              i3 \\
              gnome-games \\
              minetest \\
              network-manager \\
              xinit \\
              xserver-xorg \\
              initramfs-tools \\
              locales \\
              sudo \\
              bash \\
              coreutils \\
              fonts-noto \\
              alacritty || apt-get install -y --no-install-recommends xterm
          "

      # الخطوة 4: إعداد الدخول التلقائي بصلاحيات روت بدون كلمة مرور
      - name: إعداد الدخول التلقائي بصلاحيات روت
        run: |
          # إضافة إدخال روت لـ getty تلقائي
          sudo mkdir -p rootfs/etc/systemd/system/getty@tty1.service.d/
          sudo tee rootfs/etc/systemd/system/getty@tty1.service.d/autologin.conf > /dev/null <<'EOF'
          [Service]
          ExecStart=
          ExecStart=-/sbin/agetty --autologin root --noclear %I $TERM
          EOF

          # إعداد .bash_profile لتشغيل i3 تلقائياً عند الدخول على tty1
          sudo tee rootfs/root/.bash_profile > /dev/null <<'EOF'
          # دخول تلقائي وتشغيل i3
          if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
            exec startx
          fi
          EOF

      # الخطوة 5: إنشاء ملف إعدادات i3 مع الاختصارات المطلوبة
      - name: إنشاء ملف إعدادات i3 مع الاختصارات
        run: |
          sudo mkdir -p rootfs/etc/skel/.config/i3/
          sudo tee rootfs/etc/skel/.config/i3/config > /dev/null <<'EOF'
          # ملف إعدادات i3 - مشروع KSO-HANI V34.FINAL11
          # برمجة عبد الله و عبد الرحمن هاني [KSO]

          set $mod Mod4

          font pango:Noto Sans Arabic 10

          # Win+Enter = فتح تيرمنال
          bindsym $mod+Return exec --no-startup-id alacritty || xterm

          # Win+G = تشغيل gnome-games
          bindsym $mod+g exec --no-startup-id gnome-games

          # Win+M = تشغيل minetest
          bindsym $mod+m exec --no-startup-id minetest

          # Win+Q = إغلاق الجهاز فوراً
          bindsym $mod+q exec --no-startup-id shutdown -h now

          # إعداد الماوس
          floating_modifier $mod

          # شريط الحالة
          bar {
              status_command date
              position top
              colors {
                  background #1a1a1a
                  statusline #00ff00
              }
          }

          # ألوان النوافذ
          client.focused          #00aa00 #005500 #ffffff #00ff00 #00aa00
          client.unfocused        #333333 #222222 #888888 #292d2e #222222

          # تشغيل مدير الشبكة تلقائياً
          exec --no-startup-id nm-applet

          # استعادة ملف الإعدادات
          bindsym $mod+Shift+c reload
          bindsym $mod+Shift+r restart
          EOF

          # نسخ الإعدادات لمجلد روت أيضاً
          sudo mkdir -p rootfs/root/.config/i3/
          sudo cp rootfs/etc/skel/.config/i3/config rootfs/root/.config/i3/config

      # الخطوة 6: إعداد xinitrc لتشغيل i3
      - name: إعداد xinitrc
        run: |
          sudo tee rootfs/root/.xinitrc > /dev/null <<'EOF'
          #!/bin/bash
          exec i3
          EOF
          sudo chmod +x rootfs/root/.xinitrc

      # الخطوة 7: إعداد بنية مجلدات ISO
      - name: إعداد بنية مجلدات ISO
        run: |
          sudo mkdir -p iso/live
          sudo mkdir -p iso/boot/grub
          sudo mkdir -p iso/EFI/BOOT

      # الخطوة 8: نسخ kernel و initrd
      - name: نسخ vmlinuz و initrd.img
        run: |
          # البحث عن الكيرنل المثبت
          KERNEL=$(ls rootfs/boot/vmlinuz-* | head -1)
          INITRD=$(ls rootfs/boot/initrd.img-* | head -1)

          echo "الكيرنل المستخدم: $KERNEL"
          echo "الـ initrd المستخدم: $INITRD"

          sudo cp "$KERNEL" iso/live/vmlinuz
          sudo cp "$INITRD" iso/live/initrd.img

      # الخطوة 9: ضغط النظام بـ squashfs
      - name: ضغط النظام بـ mksquashfs
        run: |
          sudo mksquashfs rootfs iso/live/filesystem.squashfs -comp xz -noappend
          echo "حجم الـ squashfs:"
          ls -lh iso/live/filesystem.squashfs

      # الخطوة 10: إنشاء ملف GRUB مع شاشة بوت خضراء وخيارات nomodeset و toram
      - name: إنشاء ملف GRUB
        run: |
          sudo tee iso/boot/grub/grub.cfg > /dev/null <<'GRUBEOF'
          # GRUB config - KSO-HANI V34.FINAL11
          # برمجة عبد الله و عبد الرحمن هاني [KSO]

          set default=0
          set timeout=10

          insmod all_video
          insmod gfxterm
          insmod png

          # خلفية سوداء مع نص أخضر
          terminal_output gfxterm
          set color_normal=green/black
          set color_highlight=black/green
          set menu_color_normal=green/black
          set menu_color_highlight=black/green

          menuentry "KSO-HANI V34.FINAL11 [KSO] - تشغيل مباشر" --class linux {
              echo "برمجة عبد الله و عبد الرحمن هاني [KSO]"
              linux /live/vmlinuz boot=live toram nomodeset quiet splash
              initrd /live/initrd.img
          }

          menuentry "KSO-HANI V34.FINAL11 [KSO] - وضع التوافق" --class linux {
              echo "برمجة عبد الله و عبد الرحمن هاني [KSO]"
              linux /live/vmlinuz boot=live nomodeset noapic quiet splash
              initrd /live/initrd.img
          }

          menuentry "KSO-HANI V34.FINAL11 [KSO] - وضع الاسترداد" --class linux {
              echo "برمجة عبد الله و عبد الرحمن هاني [KSO]"
              linux /live/vmlinuz boot=live nomodeset single
              initrd /live/initrd.img
          }
          GRUBEOF

      # الخطوة 11: عرض رسالة ترحيبية خضراء عند البوت
      - name: إضافة رسالة ترحيبية في /etc/motd
        run: |
          sudo tee rootfs/etc/motd > /dev/null <<'EOF'

          \033[0;32m
          ██╗  ██╗███████╗ ██████╗
          ██║ ██╔╝██╔════╝██╔═══██╗
          █████╔╝ ███████╗██║   ██║
          ██╔═██╗ ╚════██║██║   ██║
          ██║  ██╗███████║╚██████╔╝
          ╚═╝  ╚═╝╚══════╝ ╚═════╝

          برمجة عبد الله و عبد الرحمن هاني [KSO]
          KSO-HANI V34.FINAL11 - Ubuntu 24.04 Noble
          \033[0m

          EOF

      # الخطوة 12: بناء ملف ISO النهائي بـ grub-mkrescue
      - name: بناء ISO النهائي بـ grub-mkrescue
        run: |
          sudo grub-mkrescue -o KSO-HANI-V34.FINAL11.iso iso -volid "KSO-HANI-V34"
          echo "✅ تم بناء الـ ISO بنجاح!"
          ls -lh KSO-HANI-V34.FINAL11.iso

      # الخطوة 13: رفع الـ ISO كـ Artifact
      - name: رفع الـ ISO كـ GitHub Artifact
        uses: actions/upload-artifact@v4
        with:
          name: KSO-HANI-V34.FINAL11-ISO
          path: KSO-HANI-V34.FINAL11.iso
          retention-days: 90
"""

def انشاء_مجلدات():
    """إنشاء مجلد .github/workflows/"""
    المسار = os.path.join(".github", "workflows")
    os.makedirs(المسار, exist_ok=True)
    print(f"✅ تم إنشاء المجلد: {المسار}")
    return المسار

def كتابة_ملف_البناء(المسار):
    """كتابة ملف build.yml"""
    مسار_الملف = os.path.join(المسار, "build.yml")
    with open(مسار_الملف, "w", encoding="utf-8") as الملف:
        الملف.write(BUILD_YML)
    print(f"✅ تم إنشاء الملف: {مسار_الملف}")

def الرئيسية():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("  مشروع KSO-ISO-Factory")
    print("  برمجة عبد الله و عبد الرحمن هاني [KSO]")
    print("=" * 60)
    print()

    # إنشاء المجلدات
    المسار = انشاء_مجلدات()

    # كتابة ملف البناء
    كتابة_ملف_البناء(المسار)

    print()
    print("=" * 60)
    print("✅ تم انشاء الملفات بنجاح. نزل المشروع ZIP وارفعه GitHub > Actions > Run workflow")
    print("=" * 60)

if __name__ == "__main__":
    الرئيسية()
