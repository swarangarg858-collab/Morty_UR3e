import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle
from pathlib import Path

OUT = Path('/mnt/c/Users/ragha/Downloads/morty_vla-main/morty-workcell-dimensions.png')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
fig = plt.figure(figsize=(15,10), facecolor='#fbfaf7')
fig.text(.06,.955,'MORTY WORKCELL — DIMENSIONED REFERENCE',fontsize=19,weight='bold',color='#18212b')
fig.text(.06,.925,'Front elevation and top view • current URDF dimensions • all labels in cm',fontsize=11,color='#52606d')
ax1=fig.add_axes([.05,.13,.45,.74]); ax2=fig.add_axes([.53,.13,.43,.74])
for ax in (ax1,ax2):
    ax.set_facecolor('#fbfaf7'); ax.axis('off')

# Common styling
base='#27313d'; taper='#596572'; collar='#1688a5'; post='#74808a'; charger='#202b36'; arm='#287db0'; dim='#b25322'; guide='#9aa5af'

def dim_h(ax,x1,x2,y,label,offset=2,color=dim):
    ax.annotate('',(x2,y),(x1,y),arrowprops=dict(arrowstyle='<->',color=color,lw=1.5,shrinkA=0,shrinkB=0))
    ax.text((x1+x2)/2,y+offset,label,ha='center',va='bottom',color=color,weight='bold',fontsize=10,clip_on=False)
def dim_v(ax,x,y1,y2,label,color=dim,side='right'):
    ax.annotate('',(x,y2),(x,y1),arrowprops=dict(arrowstyle='<->',color=color,lw=1.5,shrinkA=0,shrinkB=0))
    ha='left' if side=='right' else 'right'
    dx=1.2 if side=='right' else -1.2
    ax.text(x+dx,(y1+y2)/2,label,ha=ha,va='center',rotation=90,color=color,weight='bold',fontsize=9,clip_on=False)

# Front elevation: X-Z, charger lies on negative X side.
ax1.set_xlim(-54,46); ax1.set_ylim(-7,122); ax1.set_aspect('auto')
ax1.text(-50,118,'FRONT / SIDE VIEW  (X–Z)',weight='bold',fontsize=13,color='#18212b')
# Charger, 15 cm depth along X after 90-degree yaw; 50 wide out of page.
ax1.add_patch(Rectangle((-39.5,0),15,30,facecolor=charger,edgecolor='#111922',lw=1.5))
ax1.text(-32,15,'CHARGER\n50 L × 15 D × 30 H',ha='center',va='center',color='white',fontsize=9,weight='bold')
# Pedestal mesh-derived sizes, post begins 3 cm into collar.
ax1.add_patch(Rectangle((-22.5,0),45,16,facecolor=base,edgecolor='#111922',lw=1.4))
ax1.add_patch(Polygon([(-20,16),(20,16),(15,45),(-15,45)],closed=True,facecolor=taper,edgecolor='#303a44',lw=1.4))
ax1.add_patch(Rectangle((-17,45),34,3,facecolor=collar,edgecolor='#0d647a',lw=1.2))
# Rod: overall box bottom z=45, top z=110, with 3 cm overlap into the collar.
ax1.add_patch(Rectangle((-4,45),8,65,facecolor=post,edgecolor='#3c4650',lw=1.4))
# Side cylinder: center at x=-6.5, z=93.75; axial length 13 along X and diameter 13.
ax1.add_patch(Rectangle((-13,87.25),13,13,facecolor='#424d59',edgecolor='#18212b',lw=1.5))
# Arm mount point and schematic arm links (not dimensioned).
ax1.plot([-13,-24,-29], [93.75,96,89], color=arm,lw=6,solid_capstyle='round')
ax1.add_patch(Circle((-29,89),2.2,facecolor=arm,edgecolor='#155375',lw=1))
ax1.text(-31,104,'UR3e arm attaches\nat cylinder end',ha='center',va='bottom',color=arm,fontsize=9,weight='bold')
ax1.text(1,75,'square post\n8 × 8 cm',ha='left',va='center',color='#29323b',fontsize=9)
ax1.text(19,10,'base Ø45 × 16 H\ntaper Ø40→30 × 29 H\ncollar Ø34 × 3 H',ha='left',va='center',color='#29323b',fontsize=9)
# Central hole note with leader.
ax1.annotate('Ø12 cm center hole',xy=(0,48),xytext=(-15,59),color='#235f75',fontsize=9,weight='bold',arrowprops=dict(arrowstyle='->',color='#235f75',lw=1.2))
# Key height dimensions.
dim_v(ax1,-45,0,110,'110 cm floor to post top',side='left')
dim_v(ax1,22,45,110,'65 cm post',side='right')
dim_v(ax1,10,93.75,110,'16.25 cm below top',side='right')
ax1.annotate('side cylinder: Ø13 × 13 cm\ncenter height = 93.75 cm',xy=(-6.5,93.75),xytext=(6,120),ha='left',va='top',fontsize=9,color=dim,weight='bold',arrowprops=dict(arrowstyle='->',color=dim,lw=1.2))
ax1.plot([-49,20],[0,0],color='#58636e',lw=1.2)
ax1.text(-49,-5,'Floor / workcell z = 0',fontsize=9,color='#52606d')

# Top view: X-Y footprint and center clearances.
ax2.set_xlim(-51,27); ax2.set_ylim(-44,45); ax2.set_aspect('equal')
ax2.text(-50,42,'TOP VIEW  (X–Y)',weight='bold',fontsize=13,color='#18212b')
# charger rotated 90 degrees: 15 cm across X, 50 cm across Y.
ax2.add_patch(Rectangle((-39.5,-25),15,50,facecolor=charger,edgecolor='#111922',lw=1.5))
ax2.text(-32,0,'CHARGER\ncenter\n(-32, 0)',ha='center',va='center',color='white',fontsize=9,weight='bold',rotation=90)
# Base / post footprints.
ax2.add_patch(Circle((0,0),22.5,facecolor='#27313d',edgecolor='#111922',alpha=.85,lw=1.3))
ax2.add_patch(Circle((0,0),6,facecolor='#fbfaf7',edgecolor='#1688a5',lw=1.2))
ax2.add_patch(Rectangle((-4,-4),8,8,facecolor=post,edgecolor='#3c4650',lw=1.2))
# cylinder footprint, runs from -13 to 0; arm attaches at outer face x=-13.
ax2.add_patch(Rectangle((-13,-6.5),13,13,facecolor='#424d59',edgecolor='#18212b',lw=1.5))
ax2.plot(-13,0,marker='o',ms=6,color=arm)
ax2.annotate('UR3e mount at (-13, 0)',xy=(-13,0),xytext=(-12,12),color=arm,fontsize=9,weight='bold',arrowprops=dict(arrowstyle='->',color=arm,lw=1.2))
# Center-to-center dimensions outside the charger footprint.
dim_h(ax2,-32,0,33,'32 cm  post center → charger center',offset=1)
dim_h(ax2,-32,-6.5,29,'25.5 cm  cylinder center → charger center',offset=1)
# Nearest-edge gap between charger and cylinder.
dim_h(ax2,-24.5,-13,-34,'11.5 cm nearest-surface gap',offset=-4)
ax2.annotate('charger front faces post (+X)',xy=(-24.5,20),xytext=(-18,25),ha='left',fontsize=9,color='#52606d',arrowprops=dict(arrowstyle='->',color='#52606d',lw=1.1))
ax2.text(-49,-42,'Post center is (0,0). Charger center is 32 cm away on the charger-facing side.',fontsize=9,color='#52606d')
fig.text(.05,.055,'Note: arm links are schematic (not dimensioned). STL-derived pedestal sizes; post/cylinder/charger positions are from the current Xacro.',fontsize=9,color='#52606d')
fig.savefig(OUT,dpi=170,bbox_inches='tight',facecolor=fig.get_facecolor())
print(OUT)



