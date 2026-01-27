from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Talent, Comment, Like
from .forms import TalentForm, CommentForm
from core.decorators.customer_required import customer_required

def talent_list(request):
    talents = Talent.objects.all().order_by('-created_at')
    ad_links = [
        'https://www.effectivegatecpm.com/jp604fzw?key=0ac38e5ac8cfdc4296fa7f9060dcb6aa',
        'https://www.effectivegatecpm.com/sqf24i6k9?key=69bd5c9b5bc46a7bf95c51f8a22d72be',
        'https://www.effectivegatecpm.com/ghvacaxk?key=152c6ad3137dfd992107cafb20ba5475',
        'https://www.effectivegatecpm.com/y56j06mc56?key=8a8851afe3dc03e0d7ad3a66474de43d',
        'https://www.effectivegatecpm.com/cdrnmt82a0?key=f324af40210b539b89a9b3648da6d1a6',
        'https://www.effectivegatecpm.com/x127x1tt?key=057c2839b78ce9b3e3d4222043664ed1',
        'https://www.effectivegatecpm.com/t8969tvrft?key=a7ad665ecba681e29abdc931553dded0',
        'https://www.effectivegatecpm.com/ue2x9peh?key=edf04c7d5e5bf35cb005016b6dc7e7c7',
        'https://www.effectivegatecpm.com/bh2zyhrc?key=1e19b0229c99212775e63f84220c3f4d',
    ]
    return render(request, 'talents/talent_list.html', {'talents': talents, 'ad_links': ad_links})


def talent_detail(request, pk):
    talent = get_object_or_404(Talent, pk=pk)
    comments = talent.comments.all()
    ad_links = [
        'https://www.effectivegatecpm.com/jp604fzw?key=0ac38e5ac8cfdc4296fa7f9060dcb6aa',
        'https://www.effectivegatecpm.com/sqf24i6k9?key=69bd5c9b5bc46a7bf95c51f8a22d72be',
        'https://www.effectivegatecpm.com/ghvacaxk?key=152c6ad3137dfd992107cafb20ba5475',
        'https://www.effectivegatecpm.com/y56j06mc56?key=8a8851afe3dc03e0d7ad3a66474de43d',
        'https://www.effectivegatecpm.com/cdrnmt82a0?key=f324af40210b539b89a9b3648da6d1a6',
        'https://www.effectivegatecpm.com/x127x1tt?key=057c2839b78ce9b3e3d4222043664ed1',
        'https://www.effectivegatecpm.com/t8969tvrft?key=a7ad665ecba681e29abdc931553dded0',
        'https://www.effectivegatecpm.com/ue2x9peh?key=edf04c7d5e5bf35cb005016b6dc7e7c7',
        'https://www.effectivegatecpm.com/bh2zyhrc?key=1e19b0229c99212775e63f84220c3f4d',
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


