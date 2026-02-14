# TinyMCE Cloudinary Image Upload Integration

## Overview

The TinyMCE editor now supports direct image uploads to Cloudinary. When users paste, drag, or insert images while editing blog content, the images are automatically uploaded to Cloudinary instead of the local server.

## ✅ Features

- **Direct Upload**: Users can paste, drag-drop, or insert images directly in the TinyMCE editor
- **Cloudinary Storage**: All editor images are stored in Cloudinary (`blog_content_images` folder)
- **Automatic Optimization**: Cloudinary automatically optimizes and converts images to WebP
- **No Local Storage**: Editor images don't consume server storage
- **CDN Delivery**: Images served from Cloudinary's global CDN for faster loading
- **Seamless Integration**: Works transparently with existing blog creation/editing

## 🔧 How It Works

### 1. User Edits Blog with Images

When a user creates or edits a blog:
1. They enter content in the TinyMCE editor
2. They paste/drag/insert an image
3. TinyMCE automatically uploads the image to our endpoint

### 2. Request Flow

```
User pastes image in TinyMCE editor
        ↓
TinyMCE POST to /api/upload-tinymce-image/
        ↓
Our Django view receives the image
        ↓
Validates file (size, format)
        ↓
Uploads to Cloudinary using cloudinary.uploader
        ↓
Returns image URL to TinyMCE
        ↓
TinyMCE inserts <img> tag with Cloudinary URL
        ↓
User sees image in editor
        ↓
When blog is saved, the img tag with Cloudinary URL is stored in database
```

### 3. Image Storage

All editor images go to: `blog_content_images/` folder in Cloudinary

This is separate from:
- `blog_thumbnails/` - Blog thumbnail images
- Other content folders

## 📋 Requirements

- ✅ Cloudinary account (required - from previous setup)
- ✅ Cloudinary credentials in `.env` (from previous setup)
- ✅ User must be logged in (authentication required)
- ✅ User must have customer account (customer_required decorator)

## 🚀 Usage

### Creating a Blog with Images

1. Go to **Create Blog** or **Add Blog**
2. Click in the **Content** field (TinyMCE editor)
3. One of these options:
   - **Paste Image**: Ctrl+V (or Cmd+V on Mac) to paste an image
   - **Drag & Drop**: Drag an image file from your computer into the editor
   - **Insert Image**: Use the Image button in the toolbar
4. Cloudinary automatically uploads the image
5. You'll see the image appear in the editor
6. Click **Publish Blog Post**
7. Blog is saved with Cloudinary image URLs

### Editing a Blog with Images

Same process - any new images inserted will be uploaded to Cloudinary and stored with Cloudinary URLs.

## 🔐 Security

- **Authentication Required**: Only logged-in users with customer accounts can upload
- **File Validation**: 
  - Maximum 10MB per image
  - Only JPG, PNG, WebP, GIF allowed
- **Cloudinary Management**: 
  - Credentials stored in `.env` (not in code/frontend)
  - Cloudinary handles image security
  - Images stored with unique filenames

## 📊 Image Optimization by Cloudinary

When images are uploaded to Cloudinary via editor:
- JPG → Optimized JPG + WebP version
- PNG → Optimized PNG + WebP version
- GIF → WebP (if applicable)
- WebP → Already optimized

Users get the best format for their browser automatically.

## 🔧 Technical Implementation

### New Components

1. **View**: `core/views.upload_tinymce_image()`
   - Location: `core/views.py`
   - Endpoint: `/api/upload-tinymce-image/`
   - Method: POST
   - Authentication: login_required + customer_required

2. **URL Route**: Added to `core/urls.py`
   ```python
   path('api/upload-tinymce-image/', views.upload_tinymce_image, name='upload_tinymce_image')
   ```

3. **TinyMCE Config**: Updated in `Commerce/settings.py`
   ```python
   TINYMCE_DEFAULT_CONFIG = {
       ...
       'images_upload_url': '/api/upload-tinymce-image/',
       'images_upload_credentials': True,
       'automatic_uploads': True,
   }
   ```

### API Endpoint

**URL:** `/api/upload-tinymce-image/`
**Method:** POST
**Authentication:** Required (login + customer)

**Request:**
- Form data with `file` parameter (image file)

**Success Response (200):**
```json
{
    "location": "https://res.cloudinary.com/xxx/image/upload/v123456/blog_content_images/filename.jpg"
}
```

**Error Response (400/500):**
```json
{
    "error": "Error message describing what went wrong"
}
```

### Cloudinary Integration

Uses Django's `cloudinary` Python SDK:
- Configured with credentials from `settings.CLOUDINARY_STORAGE`
- Uploads to `blog_content_images` folder
- Uses secure URLs (`secure_url`)
- Preserves original filename with unique timestamp

## ⚙️ Configuration in Settings

```python
TINYMCE_DEFAULT_CONFIG = {
    'height': 300,
    'plugins': 'advlist autolink lists link image charmap print preview hr anchor pagebreak',
    'toolbar_mode': 'floating',
    'menubar': False,
    'toolbar': 'undo redo | formatselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | link image',
    'image_advtab': False,
    'paste_data_images': True,
    'content_css': '/static/css/tinymce_custom.css',
    'images_upload_url': '/api/upload-tinymce-image/',  # Our endpoint
    'images_upload_credentials': True,  # Send auth cookies
    'file_picker_types': 'image',
    'automatic_uploads': True,  # Auto-upload on paste/drop
}
```

## 🧪 Testing

### Test 1: Paste Image
1. Go to Create Blog
2. Click in content editor
3. Copy an image to clipboard (or use screenshot)
4. Paste with Ctrl+V
5. Should see upload progress
6. Image appears in editor with Cloudinary URL

### Test 2: Drag & Drop
1. Go to Create Blog
2. Drag an image file into the content editor
3. Should see upload progress
4. Image appears with Cloudinary URL

### Test 3: Insert via Toolbar
1. Go to Create Blog
2. Click Image button in toolbar
3. Upload dialog appears
4. Select image from device
5. Image uploads to Cloudinary
6. Appears in editor

### Test 4: Mixed Images
1. Upload one image as blog thumbnail (local or Cloudinary)
2. Add another image in editor content (auto goes to Cloudinary)
3. Publish blog
4. Verify both images display correctly
5. Check blog source - editor image should have Cloudinary URL

## 🐛 Troubleshooting

### Issue: "Upload failed" error in TinyMCE

**Possible Causes:**
1. Cloudinary credentials not configured
2. User not logged in or not authorized
3. Image file too large (>10MB)
4. Invalid image format

**Solutions:**
- Check `.env` has valid Cloudinary credentials
- Verify you're logged in with customer account
- Reduce image size to <10MB
- Use JPG, PNG, WebP, or GIF format

### Issue: Images appear as broken links

**Possible Causes:**
1. Cloudinary URL not preserved when saving blog
2. Blog content cleaning removed image tags
3. Security issue with Cloudinary URL format

**Solutions:**
- Check blog in database - URL should start with `https://res.cloudinary.com`
- Review content cleaning logic in `core/models.py`
- Verify Cloudinary account is active

### Issue: "Authentication required" error

**Cause:** User is not logged in or session expired

**Solution:**
- Log in again
- Check that you're on an authenticated session
- Clear browser cache if needed

### Issue: The upload endpoint returns 405 error

**Cause:** Using GET instead of POST

**Solution:**
- This is a TinyMCE configuration issue
- Verify `images_upload_url` is set correctly in settings
- Check browser console for errors
- Refresh page and try again

## 📈 Performance Impact

- ✅ **Minimal Server Load**: Images uploaded directly to Cloudinary, not through server
- ✅ **Faster User Experience**: CDN delivery of images
- ✅ **Storage Savings**: No local disk usage for editor images
- ✅ **Bandwidth Optimization**: Cloudinary compression
- ✅ **Auto Scaling**: Cloudinary handles peak loads

## 🔄 Compatibility

Works with:
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ✅ Mobile browsers (if supported)

Supported Actions:
- ✅ Paste image (Ctrl+V)
- ✅ Drag & drop
- ✅ Insert via toolbar
- ✅ Copy/paste URLs
- ✅ Screenshot paste

## 📚 Related Documentation

- **CLOUDINARY_SETUP_GUIDE.md** - Overall Cloudinary setup
- **CLOUDINARY_IMPLEMENTATION_SUMMARY.md** - Thumbnail upload implementation
- **CLOUDINARY_IMPLEMENTATION_NOTES.md** - General configuration notes

## 🆘 Support

If you encounter issues:

1. **Check Cloudinary Credentials**
   - Verify `.env` is configured
   - Confirm Cloud Name, API Key, API Secret are correct

2. **Check Browser Console**
   - Open F12 Developer Tools
   - Look for JavaScript errors
   - Check Network tab for failed requests

3. **Check Server Logs**
   - Look for 500 errors in Django logs
   - Check if exception is logged in logger output

4. **Test Manually**
   - Try uploading a small test image first
   - Verify other blog features work
   - Try in different browser

## 🎯 Next Steps

1. ✅ Configure Cloudinary (from previous setup)
2. ✅ Restart Django application
3. ✅ Test image upload in blog content editor
4. ✅ Monitor Cloudinary dashboard for uploaded images
5. ✅ Adjust image optimization settings as needed

---

**Version:** 1.0  
**Feature:** TinyMCE + Cloudinary Integration  
**Status:** ✅ Ready for Production  
**Date:** February 13, 2026
