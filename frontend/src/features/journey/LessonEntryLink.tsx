import {createPath,Link,useResolvedPath,type LinkProps} from 'react-router'
import {useJourneyCloud} from './journeyCloudContext'

type Props=Pick<LinkProps,'to'|'children'|'className'|'aria-label'|'onClick'|'target'|'download'>

/** Use the same cover / hold / reveal timing as the lesson's return action. */
export function LessonEntryLink({onClick,target,...props}:Props){
 const cloud=useJourneyCloud(),destination=useResolvedPath(props.to)
 return <Link {...props} target={target} onClick={event=>{
  onClick?.(event)
  if(event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||(target&&target!=='_self')||event.currentTarget.hasAttribute('download')||!cloud)return
  // A second click must not bypass an already active cloud transition.
  event.preventDefault()
  cloud.travel({destination:createPath(destination),returning:true})
 }}/>
}
