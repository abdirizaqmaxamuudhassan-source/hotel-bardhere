from django.contrib import admin

from .models import ContactMessage, GalleryImage, MenuCategory, MenuItem, Service, SiteSetting

admin.site.register(SiteSetting)
admin.site.register(Service)
admin.site.register(GalleryImage)
admin.site.register(MenuCategory)
admin.site.register(MenuItem)
admin.site.register(ContactMessage)
