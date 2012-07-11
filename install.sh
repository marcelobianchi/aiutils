#!/bin/bash 
#
#    This file is part of aiUtils.
#
#    aiUtils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    aiUtils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
#

fixSc3() {
	if [ ! -z "$SUDO_USER" ];then
		where=`awk -F":" -v user=${SUDO_USER} '$1==user {print $6}' /etc/passwd`
	fi
	[ -z "$where" ] && where=${HOME}	

	if [ -e "$BASE/seiscomp" ]; then
		if [ ! -e $BASE/seiscomp/db/generic ]; then
			echo "Current seiscomp support files/link is invalid."
			echo "Remove it or adjust it to a valid location."
			return 1
		fi
		echo "Current seiscomp support files/link already exists" && return 0
	fi

	if [ -d "$where/seiscomp3/lib/python/seiscomp" ];then
		echo "Found sc3 libs @ $where/seiscomp3/lib/python/seiscomp"
		ln -s $where/seiscomp3/lib/python/seiscomp $BASE/
		return 0
	else
		echo ""
		echo "Could not find the seiscomp python libraries folder."
		echo "Make sure that you have seiscomp3 installed at your home folder or link it from the"
		echo "\${SEISCOMP_ROOT}/lib/python/seiscomp -> seiscomp on the aiUtils folder."
		echo ""
		echo "Or if you want, I could also download the necessary files for you."
		ans="Z"
		while [ "$ans" != "N" -a "$ans" != "Y" ]; do
			read -p "Should I do it [y/n]? " ans
			ans=$(echo $ans | tr "[:lower:]" "[:upper:]" | cut -c1)
			if [ "$ans" == "Y" ]; then
				bzr branch lp:~m-tchelo/+junk/seiscomp
				return 0
			fi
		done
	fi


	echo "Installation will abort"
	return 1
}

addWrapper(){
	[ ! -f "$BASE/$1.py" ] && echo "Invalid program name" && return 1

	if [ ! -z "$SUDO_USER" ];then
		home=`awk -F":" -v user=${SUDO_USER} '$1==user {print $6}' /etc/passwd`
	else
		home=${HOME}
	fi

	[ -w "/usr/local/bin/" ] && where="/usr/local/bin" || where="$home/bin"

	echo "Creating $where/$1"
	temp=`mktemp`
	cat <<EOF > $temp
#!/bin/bash

python $BASE/$1.py \$*
EOF

	install -D -m 755 "$temp" "$where/$1"
	[ $? -ne 0 ] && echo "Failed creating wrapper, exiting" && return 1
	[ -f "$temp" ] && rm "$temp"
	return 0
}

BASE=`dirname $0`
BASE=$(cd $BASE && pwd)

echo "Installing from $BASE"

fixSc3 || exit
addWrapper aiValidate || exit
addWrapper ai2Table || exit
