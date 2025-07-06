# Course Advertisement System

## Overview

The LMS now includes a course advertisement system that displays an advertisement before users access a course. This helps generate revenue while users are browsing courses.

## Managing the Advertisement System

### Enabling/Disabling Advertisements

Administrators can easily control whether advertisements are displayed before free courses:

1. Log in to the admin panel
2. Navigate to: `/admin/lms/sitesettings/1/change/`
3. Check or uncheck the "Show Ads Before Free Courses" option
4. Save the changes

When ads are disabled, users will be redirected directly to the course page without seeing advertisements.

### Setting Courses as Free or Paid

To control which courses display advertisements:

1. Log in to the admin panel
2. Navigate to: `/admin/lms/course/`
3. Select a course to edit
4. Set the "Is Free" field to True or False:
   - **True**: Course is free and will show ads (if enabled in site settings)
   - **False**: Course is paid and will never show ads
5. Save the changes

Note: Advertisements are only shown for free courses, and only when enabled in site settings.

## Features

- Displays Google AdSense ads before users can access course content
- 5-second countdown timer before users can proceed to the course
- Support for both free and paid courses (currently all courses are set as free)
- Responsive design that works on all device sizes

## How to Configure Google AdSense

1. Sign in to your Google AdSense account at https://www.google.com/adsense
2. Create a new ad unit for course advertisements
3. Copy the ad code provided by Google

### Updating the Ad Code

To update the ad code with your own Google AdSense code:

1. Edit the file: `/lms/templates/lms/partials/ad_unit.html`
2. Replace the placeholder code with your actual Google AdSense code:

```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-YOUR_PUBLISHER_ID"
     crossorigin="anonymous"></script>
<!-- Course Access Ad -->
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-YOUR_PUBLISHER_ID"
     data-ad-slot="YOUR_AD_SLOT_ID"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({});
</script>
```

3. Replace `YOUR_PUBLISHER_ID` with your Google AdSense publisher ID
4. Replace `YOUR_AD_SLOT_ID` with your ad slot ID

## Setting Course Payment Status

Currently, all courses are set as free by default. To change a course to paid:

1. Go to the admin panel: `/admin/lms/course/`
2. Edit the course you want to change
3. Uncheck the "Is free" checkbox
4. Save the changes

## Customizing the Advertisement Page

You can customize the advertisement page by editing:
- `/lms/templates/lms/course_ad.html` - Main template
- `/lms/templates/lms/partials/ad_unit.html` - Ad unit partial template

## Bypassing Advertisements (Admin/Instructor Access)

Instructors and administrators can bypass advertisements by using:
- Direct URL: `/lms/courses/<slug>/direct/`
- Or programmatically with `course.get_direct_url()`
