import json
from pathlib import Path
from build_workflows import STYLE
if Path(__file__).with_name('manifest.json').exists():
 raise SystemExit('Refusing to overwrite the reviewed manifest. Edit its current prompts directly.')
subjects=[
('puppy','animals','A cute tan puppy sitting with two floppy ears, holding one large turquoise slipper in its mouth','The puppy gently wags its tail and tilts its head, keeping the slipper in its mouth'),
('penguin','animals','A smiling black and white penguin with an orange beak and feet standing on a simple pale blue ice floe','The penguin wiggles its flippers and sways happily from side to side'),
('kangaroo','animals','A friendly orange kangaroo with a small joey peeking out of its pouch, two long ears, big feet and a thick curved tail','The kangaroo gently bobs while the joey peeks up and waves one small paw'),
('snail','animals','A friendly green snail with a large orange shell containing one broad yellow spiral, two rounded eye stalks','The snail slowly glides forward a short distance and wiggles its eye stalks'),
('butterfly','animals','One smiling butterfly with four broad symmetrical wings, purple outer wing sections and large turquoise and yellow inner panels, a simple coral body','The butterfly slowly flaps its four wings while hovering in place'),
('octopus','animals','A cheerful purple octopus with exactly eight short rounded arms spread clearly apart, a rounded head and two big friendly eyes, no sucker dots','The octopus gently waves its eight short arms in a friendly underwater dance'),
('toucan','animals','A friendly toucan with a large orange and yellow beak, black body and white chest, perched on one short brown branch with two green leaves','The toucan bobs its head and opens one wing, holding onto the branch'),
('sheep','animals','A fluffy smiling sheep with cream wool drawn as a few large scalloped sections, a peach face and four short brown legs','The sheep gives a gentle happy bounce and wiggles its ears'),
('cow','animals','A friendly cream and brown spotted cow with four short legs, a pink muzzle and a large golden bell on a teal collar','The cow gently nods its head and swishes its tail, the bell swinging slightly'),
('hedgehog','animals','A happy small hedgehog with a tan face and a broad brown back outlined with large rounded triangular spines, beside one large red apple','The hedgehog sniffs the apple and gives a little happy nose wiggle'),
('seal','animals','A friendly pale gray seal sitting with two front flippers, balancing one large red yellow and blue beach ball on its nose','The seal balances the ball with tiny head movements and claps its front flippers once'),
('camel','animals','A cheerful golden camel in side view, one rounded hump, four simple legs, a large teal saddle blanket with a plain yellow border','The camel sways its long neck gently and flicks its small tail'),
('rocket','adventures','A chunky toy rocket with a red nose cone and fins, cream body, one large round turquoise window and three broad orange and yellow flame sections','The rocket gently lifts a little and settles while its broad flame flickers softly'),
('hot-air-balloon','adventures','A large round hot air balloon with six wide solid red orange yellow green blue and purple vertical panels and a simple brown basket below','The balloon floats gently upward and sways from side to side, the basket remaining attached'),
('train','vehicles','A chunky colorful toy steam locomotive in side view, red cabin, blue boiler, yellow chimney, three large simple wheels, on one short gray track','The toy train rolls slowly a short distance, its wheels turn and one soft cloud of steam rises'),
('aeroplane','vehicles','A cheerful yellow and blue toy propeller airplane in three-quarter view, two broad wings, a red nose and one simple front propeller','The propeller turns slowly and the airplane gently rocks its wings in place'),
('excavator','vehicles','A chunky yellow excavator in side view with a blue cabin window, simple black tracks, one large articulated arm and a raised bucket','The excavator slowly lowers and lifts its empty bucket while its body stays still'),
('camping-tent','adventures','A coral triangular camping tent with a turquoise open doorway and purple base, beside one simple rolled yellow sleeping mat','The tent doorway flaps gently in a light breeze while the sleeping mat stays still'),
('beach-bucket','adventures','A bright blue beach bucket with a red handle, one yellow spade leaning beside it and a small simple golden sand mound','The bucket handle gently swings and the spade wobbles playfully beside the sand'),
('cupcake','treats','A cute cupcake with a turquoise ridged paper wrapper in four broad panels, a large swirl of pink icing and one red cherry with a green stem','The cupcake gives a gentle playful bounce and the cherry wobbles on the icing'),
('ice-cream','treats','An ice cream cone with three large round scoops, pink on top, mint green in the middle and yellow below, a simple golden cone with only two broad diagonal lines','The scoops gently wobble together as the cone gives a tiny happy bounce'),
('teapot','everyday','A round turquoise teapot with a coral lid and handle, a broad yellow band, beside one matching empty teacup','The teapot lid lifts slightly and settles while the teacup gives a tiny playful wiggle'),
('watering-can','everyday','A bright orange watering can with a large turquoise handle and one large simple yellow flower emblem with five petals','The watering can gently tips and pours a few large blue water drops before returning upright'),
('rain-boots','everyday','A pair of bright yellow rain boots with blue soles, beside one closed coral umbrella with a curved teal handle','The rain boots make two playful alternating little steps while the closed umbrella rocks gently'),
('present','toys','A large square purple wrapped gift box with a broad yellow ribbon and a large red bow with two simple rounded loops','The closed gift box wiggles playfully and its big bow bobs, remaining tied'),
('crayons','toys','An open turquoise box holding exactly five chunky crayons with red orange yellow green and purple tips, plain wrappers without writing','The five crayons gently bob up and down one after another inside the box'),
('xylophone','toys','A colorful toy xylophone with five broad rainbow bars on a simple wooden base and two chunky round-headed mallets beside it','The two mallets lift and gently tap alternate bars while the xylophone stays in place'),
('guitar','toys','A small cheerful coral acoustic toy guitar with a yellow sound hole ring, turquoise neck and three simple black strings','The guitar sways gently side to side and its strings lightly vibrate'),
('windmill','adventures','A simple cream windmill tower with a red roof, blue door and four broad teal sails attached at one central yellow hub','The four windmill sails turn slowly together around their central hub'),
('acorn','nature','One large golden acorn with a smooth brown cap and short stem beside one large green oak leaf with broad rounded lobes','The acorn rocks gently and the oak leaf flutters softly beside it'),
]
rows=[]
for i,(slug,category,subject,motion) in enumerate(subjects,29):
 rows.append({'id':str(i),'slug':slug,'title':slug.replace('-',' ').title(),'category':category,'seed':2026100400+i,'image_prompt':STYLE.format(subject=subject),'video_prompt':f'A charming flat 2D cartoon animation for young children. {motion}. Preserve the exact subject, proportions, bright solid colors and thick black outlines of the input picture. Keep the entire subject visible. Locked camera, plain white background, gentle smooth readable motion, no cuts, no camera zoom, no text, no new objects. End near the starting pose. No speech.','image_model':'Qwen-Image-2.1','video_model':'MiniMax-H3','status':'planned'})
Path(__file__).with_name('manifest.json').write_text(json.dumps({'batch':'2026-10-04','workflow':'rainbow-paint-by-numbers','analytics_property':'557245199','levels':rows},indent=2)+'\n')
