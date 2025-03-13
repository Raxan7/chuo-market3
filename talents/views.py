from django.shortcuts import render, get_object_or_404, redirect
from .models import Talent, Comment, Like
from .forms import TalentForm, CommentForm
from django.contrib.auth.decorators import login_required

def talent_list(request):
    talents = Talent.objects.all().order_by('-created_at')
    return render(request, 'talents/talent_list.html', {'talents': talents})


def talent_detail(request, pk):
    talent = get_object_or_404(Talent, pk=pk)
    comments = talent.comments.all()
    return render(request, 'talents/talent_detail.html', {'talent': talent, 'comments': comments})


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


@login_required
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


