"""Reproducible ComfyUI API graphs and editable UI workflows for Rainbow Paint."""
import argparse, json, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def node(kind, **inputs):
    return {'class_type': kind, 'inputs': inputs}

def image_graph(prompt, seed, prefix):
    return {
        '1': node('UNETLoader', unet_name='flux2_dev_fp8mixed.safetensors', weight_dtype='default'),
        '2': node('CLIPLoader', clip_name='mistral_3_small_flux2_bf16.safetensors', type='flux2', device='default'),
        '3': node('VAELoader', vae_name='flux2-vae.safetensors'),
        '4': node('CLIPTextEncode', clip=['2',0], text=prompt),
        '5': node('FluxGuidance', conditioning=['4',0], guidance=3.5),
        '6': node('BasicGuider', model=['1',0], conditioning=['5',0]),
        '7': node('EmptyFlux2LatentImage', width=1024, height=1024, batch_size=1),
        '8': node('RandomNoise', noise_seed=seed),
        '9': node('KSamplerSelect', sampler_name='euler'),
        '10': node('Flux2Scheduler', steps=20, width=1024, height=1024),
        '11': node('SamplerCustomAdvanced', noise=['8',0], guider=['6',0], sampler=['9',0], sigmas=['10',0], latent_image=['7',0]),
        '12': node('VAEDecode', samples=['11',0], vae=['3',0]),
        '13': node('SaveImage', images=['12',0], filename_prefix=prefix),
    }

def qwen_graph(prompt, seed, prefix, reference=None):
    graph = {
        '1': node('UNETLoader', unet_name='qwen_image_2.1_int8_convrot.safetensors', weight_dtype='default'),
        '2': node('CLIPLoader', clip_name='qwen3vl_8b_int8_convrot.safetensors', type='qwen_image', device='default'),
        '3': node('VAELoader', vae_name='qwen_image_2.1_vae_bf16.safetensors'),
        '4': node('TextEncodeQwenImage21',clip=['2',0],prompt=prompt,negative_prompt='shading, gradients, noise, texture, realistic, photography, 3d, rendering, complex details, fuzzy, sketch, watermark, text, greyscale, missing eyes, extra limbs, cropped subject',resolution=1024,vae=['3',0]),
        '5': node('QwenImage21Cache', model=['1',0],device='auto',dtype='default'),
        '6': node('EmptyLatentImage',width=1024,height=1024,batch_size=1),
        '7': node('KSampler',model=['5',0],positive=['4',0],negative=['4',1],latent_image=['6',0],seed=seed,steps=25,cfg=1,sampler_name='euler',scheduler='simple',denoise=1),
        '8': node('VAEDecode',samples=['7',0],vae=['3',0]),
        '9': node('SaveImage',images=['8',0],filename_prefix=prefix),
    }
    if reference:
        graph['10']=node('LoadImage',image=reference)
        graph['4']['inputs']['images.image_1']=['10',0]
        graph['7']['inputs']['latent_image']=['4',2]
    return graph

def qwen_original_graph(prompt, seed, prefix):
    """Original installed Qwen-Image base checkpoint (Apache 2.0), text-to-image."""
    return {
        '1': node('UNETLoader', unet_name='qwen_image_fp8_e4m3fn.safetensors', weight_dtype='default'),
        '2': node('CLIPLoader', clip_name='qwen_2.5_vl_7b_fp8_scaled.safetensors', type='qwen_image', device='default'),
        '3': node('VAELoader', vae_name='qwen_image_vae.safetensors'),
        '4': node('CLIPTextEncode', clip=['2',0], text=prompt),
        '5': node('CLIPTextEncode', clip=['2',0], text='shading, gradients, texture, photography, 3d, tiny details, watermark, text, greyscale, extra limbs, cropped subject'),
        '6': node('ModelSamplingAuraFlow', model=['1',0], shift=3.1),
        '7': node('EmptySD3LatentImage', width=1024, height=1024, batch_size=1),
        '8': node('KSampler', model=['6',0], positive=['4',0], negative=['5',0], latent_image=['7',0], seed=seed, steps=50, cfg=4, sampler_name='euler', scheduler='simple', denoise=1),
        '9': node('VAEDecode', samples=['8',0], vae=['3',0]),
        '10': node('SaveImage', images=['9',0], filename_prefix=prefix),
    }

def video_graph(image, prompt, seed, prefix):
    neg='static, still image, camera movement, zoom, cuts, morphing, extra limbs, distorted face, text, watermark, flicker, gradients, realistic, scary, violence'
    return {
        '1':node('UNETLoader',unet_name='wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors',weight_dtype='default'),
        '2':node('UNETLoader',unet_name='wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors',weight_dtype='default'),
        '3':node('CLIPLoader',clip_name='umt5_xxl_fp8_e4m3fn_scaled.safetensors',type='wan',device='default'),
        '4':node('VAELoader',vae_name='wan_2.1_vae.safetensors'),
        '5':node('LoadImage',image=image),
        '6':node('CLIPTextEncode',clip=['3',0],text=prompt),
        '7':node('CLIPTextEncode',clip=['3',0],text=neg),
        '8':node('ModelSamplingSD3',model=['1',0],shift=8),
        '9':node('ModelSamplingSD3',model=['2',0],shift=8),
        '10':node('WanImageToVideo',positive=['6',0],negative=['7',0],vae=['4',0],width=640,height=640,length=81,batch_size=1,start_image=['5',0]),
        '11':node('KSamplerAdvanced',model=['8',0],positive=['10',0],negative=['10',1],latent_image=['10',2],add_noise='enable',noise_seed=seed,steps=20,cfg=3.5,sampler_name='euler',scheduler='simple',start_at_step=0,end_at_step=10,return_with_leftover_noise='enable'),
        '12':node('KSamplerAdvanced',model=['9',0],positive=['10',0],negative=['10',1],latent_image=['11',0],add_noise='disable',noise_seed=0,steps=20,cfg=3.5,sampler_name='euler',scheduler='simple',start_at_step=10,end_at_step=20,return_with_leftover_noise='disable'),
        '13':node('VAEDecode',samples=['12',0],vae=['4',0]),
        '14':node('CreateVideo',images=['13',0],fps=16),
        '15':node('SaveVideo',video=['14',0],filename_prefix=prefix,format='mp4',codec='h264'),
    }

def h3_graph(image, prompt, seed, prefix, turbo=False):
    g = {
        '1':node('UNETLoader',unet_name='minimax_h3_fl2va_pruned_int8_convrot.safetensors',weight_dtype='default'),
        '2':node('CLIPLoader',clip_name='qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors',type='minimax',device='default'),
        '3':node('VAELoader',vae_name='minimax_h3_video_vae_int8_convrot.safetensors'),
        '4':node('LoadImage',image=image),
        '5':node('MiniMaxH3ImageToVideo',clip=['2',0],vae=['3',0],prompt=prompt,width=640,height=640,length=124,first_frame=['4',0]),
        '6':node('RandomNoise',noise_seed=seed),
        '7':node('KSamplerSelect',sampler_name='res_multistep'),
        '8':node('BasicScheduler',model=['1',0],scheduler='simple',steps=20,denoise=1),
        '9':node('BasicGuider',model=['1',0],conditioning=['5',0]),
        '10':node('SamplerCustomAdvanced',noise=['6',0],guider=['9',0],sampler=['7',0],sigmas=['8',0],latent_image=['5',1]),
        '11':node('VAEDecode',samples=['10',0],vae=['3',0]),
        '12':node('CreateVideo',images=['11',0],fps=24),
        '13':node('SaveVideo',video=['12',0],filename_prefix=prefix,format='mp4',codec='h264'),
    }
    if turbo:
        g['14']=node('LoraLoaderModelOnly',model=['1',0],lora_name='minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors',strength_model=1)
        g['8']['inputs'].update(model=['14',0],steps=8)
        g['9']['inputs']['model']=['14',0]
    return g

def ui_graph(graph, catalog):
    """Build ordinary editable core nodes, preserving every edge and widget."""
    nodes=[]; links=[]; by_id={}
    for index,(key,n) in enumerate(graph.items()):
        schema=catalog[n['class_type']]; inputs=[]; widgets=[]
        for name,spec in {**schema['input'].get('required',{}),**schema['input'].get('optional',{})}.items():
            if name not in n['inputs']:continue
            value=n['inputs'][name]; kind=spec[0]
            is_link=isinstance(value,list) and len(value)==2 and str(value[0]) in graph and isinstance(value[1],int)
            if is_link: inputs.append({'name':name,'type':kind if isinstance(kind,str) else 'COMBO','link':None})
            else:
                widgets.append(value)
                if len(spec)>1 and isinstance(spec[1],dict) and spec[1].get('control_after_generate'):widgets.append('fixed')
                if n['class_type']=='LoadImage' and name=='image':widgets.append('image')
        outputs=[{'name':name,'type':kind,'links':[]} for name,kind in zip(schema.get('output_name',schema['output']),schema['output'])]
        item={'id':int(key),'type':n['class_type'],'pos':[(index%4)*380,(index//4)*350],'size':[340,260],'flags':{},'order':index,'mode':0,'inputs':inputs,'outputs':outputs,'properties':{'Node name for S&R':n['class_type']},'widgets_values':widgets}
        nodes.append(item);by_id[key]=item
    for key,n in graph.items():
        for slot,inp in enumerate(by_id[key]['inputs']):
            source,output=n['inputs'][inp['name']];link_id=len(links)+1
            inp['link']=link_id;by_id[source]['outputs'][output]['links'].append(link_id)
            links.append([link_id,int(source),output,int(key),slot,inp['type']])
    return {'last_node_id':max(map(int,graph)),'last_link_id':len(links),'nodes':nodes,'links':links,'groups':[],'config':{},'extra':{'ds':{'scale':0.7,'offset':[30,30]}},'version':0.4}

STYLE="Flat vector illustration for a young child's paint-by-numbers game. {subject}. One large cute subject, rounded simple shapes and recognizable anatomy or physical structure. Friendly faces belong only on animals; no faces, eyes, mouths or limbs on objects, plants, food or decorations. Thick smooth uniform black outlines, closed clean shapes, 7 to 9 vibrant solid flat colors, large easy-to-paint color areas, clean pure white background, centered whole subject with generous white margin on all sides. Simple 2D cartoon clipart. No lettering, no patterns of tiny shapes, no gradients, no shading, no textures, no shadows."

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Save repo workflows and optionally install them in ComfyUI')
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8188')
    parser.add_argument('--install-dir',type=Path,help='Optional ComfyUI user/default/workflows directory')
    args=parser.parse_args()
    with urllib.request.urlopen(args.comfy_url+'/object_info',timeout=60) as response:
        catalog=json.load(response)
    first=json.loads((ROOT/'manifest.json').read_text())['levels'][0]
    prompt=first['image_prompt'];motion=first['video_prompt'];seed=first['seed']
    graphs={
        'rainbow-paint-by-numbers':qwen_original_graph(prompt,seed,'rainbow-paint-by-numbers/image/29-puppy'),
        'rainbow-paint-by-numbers-rewards':video_graph('rainbow-paint-by-numbers/29.png',motion,seed,'rainbow-paint-by-numbers/video/29-puppy'),
        'rainbow-paint-by-numbers-qwen21-research':qwen_graph(prompt,seed,'rainbow-paint-by-numbers/research/image/29-puppy'),
        'rainbow-paint-by-numbers-minimax-h3-research':h3_graph('rainbow-paint-by-numbers/29.png',motion,seed,'rainbow-paint-by-numbers/research/video/29-puppy'),
        'rainbow-paint-by-numbers-flux2-fallback':image_graph(prompt,seed,'rainbow-paint-by-numbers/fallback/29-puppy'),
        'rainbow-paint-by-numbers-wan22-fallback':video_graph('rainbow-paint-by-numbers/29.png',motion,seed,'rainbow-paint-by-numbers/fallback/29-puppy'),
    }
    (ROOT/'workflows').mkdir(exist_ok=True)
    for name,g in graphs.items():
        (ROOT/'workflows'/f'{name}.api.json').write_text(json.dumps(g,indent=2))
        ui=ui_graph(g,catalog)
        ui['extra']['rainbow_model_purpose']='research/testing; review model terms before use' if name.endswith('-research') else 'established generation workflow'
        (ROOT/'workflows'/f'{name}.json').write_text(json.dumps(ui,indent=2))
        if args.install_dir:
            args.install_dir.mkdir(parents=True,exist_ok=True)
            (args.install_dir/f'{name}.json').write_text(json.dumps(ui,indent=2))
