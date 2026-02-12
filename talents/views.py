from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Talent, Comment, Like
from .forms import TalentForm, CommentForm
from core.decorators.customer_required import customer_required

def talent_list(request):
    talents = Talent.objects.all().order_by('-created_at')
    ad_links = [
        'https://otieu.com/4/10558195',
        'https://otieu.com/4/10558194',
        'https://otieu.com/4/10558193',
        'https://otieu.com/4/10558192',
        'https://otieu.com/4/10558191',
        'https://otieu.com/4/10558189',
        'https://otieu.com/4/10558188',
        'https://otieu.com/4/10558187',
        'https://otieu.com/4/10558184',
        'https://otieu.com/4/10558186',
    ]
    return render(request, 'talents/talent_list.html', {'talents': talents, 'ad_links': ad_links})


def talent_detail(request, pk):
    talent = get_object_or_404(Talent, pk=pk)
    comments = talent.comments.all()
    ad_links = [
        'https://otieu.com/4/10558195',
        'https://otieu.com/4/10558194',
        'https://otieu.com/4/10558193',
        'https://otieu.com/4/10558192',
        'https://otieu.com/4/10558191',
        'https://otieu.com/4/10558189',
        'https://otieu.com/4/10558188',
        'https://otieu.com/4/10558187',
        'https://otieu.com/4/10558184',
        'https://otieu.com/4/10558186',
    ]
    return render(request, 'talents/talent_detail.html', {'talent': talent, 'comments': comments, 'ad_links': ad_links})


@login_required
def post_talent(request):
    if request.method == 'POST':
        form = TalentForm(request.POST, request.FILES)
        if form.is_valid():
            talent = form.save(commit=False)
            talent.user = request.user
            talent.save()
            return redirect('talent_list')
    else:
        form = TalentForm()
    return render(request, 'talents/post_talent.html', {'form': form})


@login_required(login_url='login')  # Ensure this matches the LOGIN_URL in settings.py
def add_comment(request, pk):
    talent = get_object_or_404(Talent, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.talent = talent
            comment.save()
            return redirect('talent_detail', pk=pk)
    else:
        form = CommentForm()
    return render(request, 'talents/add_comment.html', {'form': form})


@login_required
def like_talent(request, pk):
    talent = get_object_or_404(Talent, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, talent=talent)
    
    if not created:
        like.delete()  # Unlike if already liked
    
    return redirect('talent_list')


@login_required
@customer_required
def edit_talent(request, pk):
    """
    Edit a talent - only the owner can edit it
    """
    talent = get_object_or_404(Talent, pk=pk)
    
    # Check if current user is the owner
    if talent.user != request.user:
        messages.error(request, "You can only edit talents that you've posted.")
        return redirect('talent_detail', pk=talent.pk)
    
    if request.method == 'POST':
        form = TalentForm(request.POST, request.FILES, instance=talent)
        if form.is_valid():
            form.save()
            messages.success(request, "Your talent post has been updated successfully.")
            return redirect('talent_detail', pk=talent.pk)
    else:
        form = TalentForm(instance=talent)
    
    return render(request, 'talents/edit_talent.html', {
        'form': form,
        'talent': talent,
    })


@login_required
@customer_required
def delete_talent(request, pk):
    """
    Delete a talent - only the owner can delete it
    """
    talent = get_object_or_404(Talent, pk=pk)
    
    # Check if current user is the owner
    if talent.user != request.user:
        messages.error(request, "You can only delete talents that you've posted.")
        return redirect('talent_detail', pk=talent.pk)
    
    if request.method == 'POST':
        # Store information for confirmation message
        talent_title = talent.title
        
        # Delete the talent
        talent.delete()
        
        messages.success(request, f"Your talent post '{talent_title}' has been deleted successfully.")
        from django.urls import reverse
        return redirect(f"{reverse('user_dashboard')}?tab=talents")  # Redirect to dashboard talents tab
    
    return render(request, 'talents/delete_talent_confirm.html', {
        'talent': talent,
    })


