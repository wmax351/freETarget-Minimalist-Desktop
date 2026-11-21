(()=>{
'use strict';
const keys=['ft-shooter-profiles-v1','ft-session-history-v1'];
const stateKey='ft-apple-sync-baseline-v1';
const uuid=/^[a-f0-9-]{36}$/i;
function sorted(value){
 if(Array.isArray(value))return value.map(sorted);
 if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,sorted(value[key])]));
 return value;
}
const canonical=value=>JSON.stringify(sorted(value));
function rows(values){
 return values.map((value,index)=>{
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error('A local sync record is invalid.');
  return [typeof value.id==='string'&&value.id?value.id:'legacy:'+canonical(value),value];
 });
}
function reconcile(device,replicas,current,baseline){
 const winners=keys.map(()=>new Map()), own=keys.map(()=>new Map());
 let clock=0;
 function accept(map,id,value,stamp,author){
  const before=map.get(id);
  if(!before||stamp>before[1]||(stamp===before[1]&&author>before[2]))map.set(id,[value,stamp,author]);
 }
 for(const replica of replicas){
  if(replica.version!==1||!uuid.test(replica.device)||!Array.isArray(replica.records)||replica.records.length!==2)throw Error('A sync file has an unsupported format.');
  replica.records.forEach((entries,index)=>{
   if(!Array.isArray(entries))throw Error('A sync file has invalid records.');
   for(const [id,value,stamp] of entries){
    if(typeof id!=='string'||!id||!Number.isSafeInteger(stamp)||stamp<1||stamp>=Number.MAX_SAFE_INTEGER||(value!==null&&rows([value])[0][0]!==id))throw Error('A sync record is invalid.');
    clock=Math.max(clock,stamp);
    accept(winners[index],id,value,stamp,replica.device);
    if(replica.device===device)accept(own[index],id,value,stamp,device);
   }
  });
 }
 current.forEach((values,index)=>{
  const before=new Map(rows(baseline[index]));
  const now=new Map(rows(values));
  for(const id of new Set([...now.keys(),...before.keys()])){
   const value=now.get(id)??null;
   const previous=before.get(id)??null;
   if(canonical(value)===canonical(previous))continue;
   if(value!==null&&canonical(winners[index].get(id)?.[0])===canonical(value))continue;
   accept(own[index],id,value,clock+1,device);
   accept(winners[index],id,value,clock+1,device);
  }
 });
 const merged=winners.map(map=>[...map.values()].map(entry=>entry[0]).filter(value=>value!==null));
 const names=merged[0].map(profile=>String(profile.name).trim().toLowerCase());
 if(new Set(names).size!==names.length)throw Error('Two separate profiles have the same name. Rename one of them on its original device, then sync again.');
 merged[0].sort((a,b)=>String(a.id??a.name).localeCompare(String(b.id??b.name)));
 merged[1].sort((a,b)=>String(a.date??'').localeCompare(String(b.date??''))||String(a.id??'').localeCompare(String(b.id??'')));
 return {merged,replica:{version:1,device,records:own.map(map=>[...map].map(([id,[value,stamp]])=>[id,value,stamp]))}};
}
if(typeof module==='object'){module.exports={reconcile};return}

document.addEventListener('DOMContentLoaded',()=>{
 const button=document.getElementById('appleSyncNow'), automatic=document.getElementById('appleSyncAutomatic');
 if(!button||!automatic||!window.FTDesktop)return;
 const status=document.getElementById('appleSyncStatus');
 const storage=window.FTDesktopStorage, preference='ft-apple-sync-automatic-v1';
 automatic.checked=storage.getItem(preference)==='true';
 let busy=false;
 const idle=()=>{
  const state=window.FTDesktopSessionState?.();
  return state&&!state.active&&!state.unsaved&&!state.connected;
 };
 const foreground=()=>!document.hidden;
 const canRunAutomatically=()=>automatic.checked&&foreground()&&document.getElementById('settingsOverlay')?.hidden;
 async function sync(auto){
  if(busy||(auto&&(!canRunAutomatically()||!idle())))return;
  busy=true;button.disabled=true;
  try{
   if(!idle())throw Error('Finish and save or discard the session, then disconnect the target before syncing.');
   if(!auto)status.textContent='Checking iCloud…';
   const result=await window.FTDesktop.request('/desktop/apple-sync-read',{automatic:auto});
   if(!idle()||(auto&&!canRunAutomatically())){
    if(!auto)status.textContent='Sync paused. Finish the session and try again.';
    return;
   }
   if(result.needsConfirmation&&!confirm('Sync shooter profiles and saved sessions with the iCloud account currently signed in on this device?')){
    status.textContent='Sync canceled.';return;
   }
   const revision=window.FTDesktop.revision;
   const current=keys.map(key=>JSON.parse(storage.getItem(key)||'[]'));
   const state=JSON.parse(storage.getItem(stateKey)||'null');
   const own=result.replicas.find(file=>file.device===result.device);
   const baseline=own&&state?.device===result.device?state.values:[[],[]];
   const {merged,replica}=reconcile(result.device,result.replicas,current,baseline);
   const values=Object.fromEntries(keys.map((key,index)=>[key,JSON.stringify(merged[index])]));
   values[stateKey]=JSON.stringify({device:result.device,values:merged});
   const recordsChanged=canonical(current)!==canonical(merged);
   if(result.needsConfirmation||recordsChanged||canonical(state)!==canonical(JSON.parse(values[stateKey]))||canonical(own)!==canonical(replica)){
    const applied=await window.FTDesktop.request('/desktop/apple-sync-apply',{token:result.token,expected_revision:revision,values,replica,publish:canonical(own)!==canonical(replica)});
    if(recordsChanged){window.location.reload();return}
    window.FTDesktop.acceptAppleSync(applied.revision,values);
   }
   status.textContent='iCloud folder checked at '+new Date().toLocaleTimeString()+'.';
  }catch(error){status.textContent=error.message}
  finally{busy=false;button.disabled=false}
 }
 button.onclick=()=>sync(false);
 automatic.onchange=()=>{
  try{
   storage.setItem(preference,String(automatic.checked));
   status.textContent=automatic.checked?'Automatic sync will run when the app is open and idle.':'Automatic sync is off. You can still use Sync Now.';
  }catch(error){automatic.checked=storage.getItem(preference)==='true';status.textContent=error.message}
 };
 window.addEventListener('focus',()=>sync(true));
 document.addEventListener('visibilitychange',()=>sync(true));
 window.setInterval(()=>sync(true),30000);
 window.setTimeout(()=>sync(true),1000);
});
})();
